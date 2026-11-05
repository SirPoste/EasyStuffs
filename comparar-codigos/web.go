package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"time"

	_ "embed"
)

//go:embed web/index.html
var indexHTML []byte

func serveWeb(stdout, stderr io.Writer) int {
	ln, err := net.Listen("tcp", "127.0.0.1:8741")
	if err != nil {
		ln, err = net.Listen("tcp", "127.0.0.1:0")
	}
	if err != nil {
		fmt.Fprintf(stderr, "Erro: %v\n", err)
		return 1
	}

	url := "http://" + ln.Addr().String()
	fmt.Fprintf(stdout, "Pagina: %s\n", url)
	fmt.Fprintln(stdout, "Feche esta janela para sair.")
	openBrowser(url)

	server := &http.Server{
		Handler:           newMux(),
		ReadHeaderTimeout: 5 * time.Second,
	}
	if err := server.Serve(ln); err != nil && err != http.ErrServerClosed {
		fmt.Fprintf(stderr, "Erro: %v\n", err)
		return 1
	}
	return 0
}

func openBrowser(url string) {
	if os.Getenv("COMPARAR_NO_BROWSER") == "1" {
		return
	}
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		cmd = exec.Command("rundll32", "url.dll,FileProtocolHandler", url)
	case "darwin":
		cmd = exec.Command("open", url)
	default:
		cmd = exec.Command("xdg-open", url)
	}
	_ = cmd.Start()
}

func newMux() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /{$}", indexHandler)
	mux.HandleFunc("POST /api/comparar", compareHandler)
	return mux
}

func indexHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	_, _ = w.Write(indexHTML)
}

type compareRequest struct {
	Codigo1 string `json:"codigo1"`
	Codigo2 string `json:"codigo2"`
}

type compareResponse struct {
	Iguais  bool   `json:"iguais"`
	S1      string `json:"s1,omitempty"`
	S2      string `json:"s2,omitempty"`
	Codigo1 string `json:"codigo1,omitempty"`
	Codigo2 string `json:"codigo2,omitempty"`
	Erro    string `json:"erro,omitempty"`
	Campo   int    `json:"campo,omitempty"`
}

func compareHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	r.Body = http.MaxBytesReader(w, r.Body, 4096)
	var req compareRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, compareResponse{Erro: "Pedido inválido."})
		return
	}
	left, err := Parse(req.Codigo1)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, compareResponse{
			Erro:  "O primeiro código não tem o formato 1# seguido de 7 dígitos e 10 dígitos.",
			Campo: 1,
		})
		return
	}
	right, err := Parse(req.Codigo2)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, compareResponse{
			Erro:  "O segundo código não tem o formato 1# seguido de 7 dígitos e 10 dígitos.",
			Campo: 2,
		})
		return
	}
	result := Compare(left, right)
	writeJSON(w, http.StatusOK, compareResponse{
		Iguais:  result.Equal(),
		S1:      left.S,
		S2:      right.S,
		Codigo1: left.Raw,
		Codigo2: right.Raw,
	})
}

func writeJSON(w http.ResponseWriter, status int, body compareResponse) {
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}
