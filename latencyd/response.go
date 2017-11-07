package main

import (
	"bytes"
	"fmt"
	"net/http"
	"text/template"
	"time"
)

var responseTemplate = func() *template.Template {
	t, err := template.New("response").
		Funcs(template.FuncMap{
			"ms": func(d time.Duration) int {
				return int(d.Nanoseconds() / 1000000)
			},
			"colorize": func(status int) string {
				if status >= 200 && status < 400 {
					return fmt.Sprintf("\x1b[32m%d\x1b[0m", status)
				}
				return fmt.Sprintf("\x1b[31m%d\x1b[0m", status)
			},
			"nullable": func(s string) string {
				if s == "" {
					return "-"
				}
				return s
			},
		}).
		Parse("{{nullable .RequestID}} {{nullable .Request.RemoteAddr}} \x1b[95mGET\x1b[0m {{.Request.URL}} {{colorize .StatusCode}} {{.ContentLength}} {{ms .Duration}}")
	if err != nil {
		panic(fmt.Sprintf("error parsing response template: %v", err))
	}
	return t
}()

type ResponseData struct {
	NodeName  string          `json:"nodeName"`
	RequestID string          `json:"requestId"`
	Error     string          `json:"error,omitempty"`
	Delay     int             `json:"delay"`
	Backends  []*ResponseData `json:"backends,omitempty"`
}

type ResponseWriter struct {
	http.ResponseWriter
	Request       *http.Request
	Written       bool
	StatusCode    int
	ContentLength int
	Duration      time.Duration
	RequestID     string
}

func (w *ResponseWriter) Write(b []byte) (int, error) {
	if !w.Written {
		w.WriteHeader(http.StatusOK)
	}
	size, err := w.ResponseWriter.Write(b)
	w.ContentLength += size
	return size, err
}

func (w *ResponseWriter) WriteHeader(s int) {
	w.Written = true
	w.StatusCode = s
	w.ResponseWriter.WriteHeader(s)
}

func (w *ResponseWriter) Header() http.Header {
	return w.ResponseWriter.Header()
}

func (w *ResponseWriter) String() string {
	b := &bytes.Buffer{}
	responseTemplate.Execute(b, w)
	return b.String()
}
