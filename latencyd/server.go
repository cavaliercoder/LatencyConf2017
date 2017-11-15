package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math/rand"
	"net/http"
	"os"
	"time"
)

type BackendConfig struct {
	Name       string `json:"name"`
	URL        string `json:"url"`
	Timeout    int    `json:"timeout"`
	RoundTrips int    `json:"roundtrips"`
}

func (b BackendConfig) String() string {
	return b.Name
}

type ServerConfig struct {
	NodeName   string          `json:"nodeName"`
	LogFile    string          `json:"logFile"`
	ListenAddr string          `json:"listenAddr"`
	Load       int             `json:"load"`
	Variance   float64         `json:"variance"`
	Backends   []BackendConfig `json:"backends"`
}

func OpenServerConfig(path string) (*ServerConfig, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	cfg := &ServerConfig{}
	dec := json.NewDecoder(f)
	if err := dec.Decode(cfg); err != nil {
		return nil, err
	}
	return cfg, nil
}

type Server struct {
	*ServerConfig

	srv    *http.Server
	ctx    context.Context
	logger *log.Logger
}

func NewServer(cfg *ServerConfig, ctx context.Context) (*Server, error) {
	var err error
	w := os.Stdout
	if cfg.LogFile != "stdout" && cfg.LogFile != "" {
		w, err = os.OpenFile(cfg.LogFile, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0640)
		if err != nil {
			return nil, fmt.Errorf("error opening log file: %v", err)
		}
	}
	srv := &Server{
		ServerConfig: cfg,
		ctx:          ctx,
		logger:       log.New(w, fmt.Sprintf("[%s] ", cfg.NodeName), log.LstdFlags),
	}
	srv.srv = &http.Server{
		Addr:     cfg.ListenAddr,
		Handler:  srv,
		ErrorLog: srv.logger,
	}
	return srv, nil
}

func (s *Server) Serve() error {
	go func() {
		<-s.ctx.Done()
		s.Shutdown()
	}()
	s.logger.Printf("Server listening on %v", s.ListenAddr)
	return s.srv.ListenAndServe()
}

func (s *Server) Shutdown() error {
	s.logger.Printf("Draining connections")
	err := s.srv.Shutdown(s.ctx)
	if err == nil {
		s.logger.Printf("Server shutdown")
		return err
	}
	s.logger.Printf("Error shutting down server: %v", err)
	return err
}

// ServeHTTP handles all HTTP requests
func (s *Server) ServeHTTP(rw http.ResponseWriter, r *http.Request) {
	start := time.Now()
	reqID := s.RequestID(r)
	rw.Header().Set("X-Request-Id", reqID)
	w := &ResponseWriter{
		ResponseWriter: rw,
		Request:        r,
		RequestID:      reqID,
	}
	statusCode := http.StatusOK

	// log access on completion
	defer func() {
		w.Duration = time.Now().Sub(start)
		s.logger.Printf("%v", w)
	}()

	// fetch data from backends
	data := &ResponseData{
		NodeName:  s.NodeName,
		RequestID: reqID,
		Backends:  []*BackendResponseData{},
	}
	for _, backend := range s.Backends {
		trips := backend.RoundTrips
		if trips < 1 {
			trips = 1
		}
		for i := 0; i < trips; i++ {
			// BUG: each roundtrip uses the same request id
			bdata, err := s.GetBackendResponse(backend, reqID)
			if err != nil {
				bdata = &BackendResponseData{
					StatusCode: http.StatusServiceUnavailable,
					ResponseData: &ResponseData{
						Error: fmt.Sprintf("error fetching backend '%s': %v", backend, err),
					},
				}
			}
			statusCode = bdata.StatusCode
			data.Backends = append(data.Backends, bdata)
		}
	}

	// introduce CPU-bound latency
	load := s.RandDelay()
	sum, err := s.DoWork(load, s.ctx)
	if err != nil {
		data.Error = fmt.Sprintf("error doing work: %v", err)
		statusCode = http.StatusInternalServerError
	}
	data.WorkDone = sum
	data.Load = load

	w.WriteHeader(statusCode)
	s.JSON(w, data)
}

// GetBackendResponse fetches JSON data from the given backend (running the same
// software) using the given Request ID. The response body is decoded and
// returned as a ResponseData struct.
func (s *Server) GetBackendResponse(backend BackendConfig, reqID string) (*BackendResponseData, error) {
	req, err := http.NewRequest("GET", backend.URL, nil)
	if err != nil {
		return nil, err
	}
	req = req.WithContext(s.ctx)
	req.Header.Set("X-Request-Id", reqID)
	client := http.Client{
		Timeout: time.Millisecond * time.Duration(backend.Timeout),
	}
	start := time.Now()
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	v := &BackendResponseData{
		Backend:      &backend,
		StatusCode:   resp.StatusCode,
		Latency:      float64(time.Now().Sub(start)) / float64(time.Millisecond),
		ResponseData: &ResponseData{},
	}
	dec := json.NewDecoder(resp.Body)
	if err := dec.Decode(v.ResponseData); err != nil {
		return nil, err
	}
	return v, nil
}

// RequestID returns a random Request ID for the given http.Request. If the
// X-Request-Id request header is set, that ID is returned instead.
func (s *Server) RequestID(r *http.Request) string {
	if v := r.Header.Get("X-Request-Id"); v != "" {
		return v
	}
	var b [16]byte
	rand.Read(b[:])
	return hex.EncodeToString(b[:])
}

// RandDelay returns a random delay duration within the desired latency variance
// for the Server.
func (s *Server) RandDelay() int {
	v := float64(s.Load)
	return int((v - (v * s.Variance)) + (v * s.Variance * rand.Float64() * 2))
}

// JSON encodes the given interface as a JSON document and writes it to the
// given ResponseWriter.
func (s *Server) JSON(w http.ResponseWriter, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	enc := json.NewEncoder(w)
	enc.SetIndent("", "  ")
	if err := enc.Encode(v); err != nil {
		s.Error(w, http.StatusInternalServerError, "error encoding %T: %v", v, err)
		return
	}
}

func (s *Server) Error(w http.ResponseWriter, statusCode int, format string, a ...interface{}) {
	err := fmt.Sprintf(format, a...)
	s.logger.Printf("\x1b[31mError\x1b[0m %v", err)
	w.WriteHeader(statusCode)
	s.JSON(w, &ResponseData{
		NodeName: s.NodeName,
		Error:    err,
	})
}

// DoWork computes the SHA256 checksum of values generated by a pseudo-random
// number generator over a period of time. Computation stops and the checksum is
// returned once the given Context is canceled.
func (s *Server) DoWork(load int, ctx context.Context) (string, error) {
	var err error
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	h := sha256.New()

	for i := 0; i < load; i++ {
		_, err = io.CopyN(h, r, 32768)
		if err != nil {
			return "", err
		}

		select {
		case <-ctx.Done():
			i = load // break
		default:
		}
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}
