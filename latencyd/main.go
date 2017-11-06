package main

import (
	"context"
	"flag"
	"fmt"
	"math/rand"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

var configFile = flag.String("config", "./config.json", "config file path")

func main() {
	flag.Parse()
	rand.Seed(time.Now().UnixNano())

	// load config file
	f, err := os.Open(*configFile)
	if err != nil {
		die("unable to open configuration file: %v", err)
	}
	defer f.Close()

	// create server
	cfg, err := LoadServerConfig(f)
	if err != nil {
		die("unable to read configuration file: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	s, err := NewServer(cfg, ctx)
	if err != nil {
		die("unable to create server: %v", err)
	}

	// listen for signals
	go func() {
		c := make(chan os.Signal, 1)
		signal.Notify(c, syscall.SIGINT, syscall.SIGTERM)
		select {
		case <-ctx.Done():
			return
		case s := <-c:
			fmt.Println("Caught signal:", s)
			cancel()
		}
		s.Shutdown()
	}()

	// start server
	err = s.Serve()
	if err == http.ErrServerClosed {
		return
	}
	if err != nil {
		die("unable to start server: %v", err)
	}
}

func die(format string, a ...interface{}) {
	fmt.Fprintf(os.Stderr, "\x1b[31mERROR\x1b[0m "+format+"\n", a...)
	os.Exit(1)
}