package main

import (
	"bytes"
	"context"
	"encoding/json"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestIndexPage(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	rec := httptest.NewRecorder()
	newMux(nil).ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("estado = %d", rec.Code)
	}
	body := rec.Body.String()
	if !strings.Contains(body, `aria-label="Audi"`) {
		t.Fatal("a pagina devia ter o logotipo da Audi")
	}
	if !strings.Contains(body, `aria-label="Bosch"`) {
		t.Fatal("a pagina devia ter o logotipo da Bosch")
	}
	if !strings.Contains(body, "AfterMarket") {
		t.Fatal("a pagina devia ter o texto AfterMarket")
	}
	bosch := strings.Index(body, `aria-label="Bosch"`)
	centro := strings.Index(body, "AfterMarket")
	audi := strings.Index(body, `aria-label="Audi"`)
	if bosch < 0 || centro < 0 || audi < 0 || !(bosch < centro && centro < audi) {
		t.Fatal("a Bosch devia ficar a esquerda, AfterMarket ao centro e a Audi a direita")
	}
	if !strings.Contains(body, "Primeiro código") || !strings.Contains(body, "Segundo código") {
		t.Fatal("faltam os campos de leitura")
	}
	if !strings.Contains(body, "function compararLocal") {
		t.Fatal("a pagina devia comparar sem o executavel")
	}
	if !strings.Contains(body, `id="sair"`) {
		t.Fatal("faltava o botao para fechar o programa")
	}
	primeiro := strings.Index(body, `id="codigo1"`)
	resultado := strings.Index(body, `id="resultado"`)
	segundo := strings.Index(body, `id="codigo2"`)
	if primeiro < 0 || resultado < 0 || segundo < 0 || !(primeiro < resultado && resultado < segundo) {
		t.Fatal("o resultado devia ficar entre os dois codigos")
	}
	if !strings.Contains(rec.Header().Get("Content-Type"), "text/html") {
		t.Fatalf("content-type = %s", rec.Header().Get("Content-Type"))
	}
}

func TestAPISameSDifferentP(t *testing.T) {
	body := postCompare(t, "1#12345671234567890", "1#12345679999999999")
	if body.Code != http.StatusOK {
		t.Fatalf("estado = %d, corpo = %s", body.Code, body.Body.String())
	}
	resp := decodeCompare(t, body)
	if !resp.Iguais || resp.S1 != "1234567" || resp.S2 != "1234567" {
		t.Fatalf("%+v", resp)
	}
}

func TestAPIDifferentS(t *testing.T) {
	body := postCompare(t, "1#12345671234567890", "1#76543211234567890")
	if body.Code != http.StatusOK {
		t.Fatalf("estado = %d", body.Code)
	}
	resp := decodeCompare(t, body)
	if resp.Iguais || resp.S1 != "1234567" || resp.S2 != "7654321" {
		t.Fatalf("%+v", resp)
	}
}

func TestAPIInvalidSecondCode(t *testing.T) {
	body := postCompare(t, "1#12345671234567890", "123")
	if body.Code != http.StatusBadRequest {
		t.Fatalf("estado = %d", body.Code)
	}
	resp := decodeCompare(t, body)
	if resp.Campo != 2 || !strings.Contains(resp.Erro, "segundo") {
		t.Fatalf("%+v", resp)
	}
}

func TestPageIsOurs(t *testing.T) {
	ours := httptest.NewServer(newMux(nil))
	t.Cleanup(ours.Close)
	if !pageIsOurs(ours.URL + "/") {
		t.Fatal("devia reconhecer a pagina")
	}

	other := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte("outra coisa"))
	}))
	t.Cleanup(other.Close)
	if pageIsOurs(other.URL + "/") {
		t.Fatal("nao devia reconhecer outra pagina")
	}

	antiga := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`<form id="leitura"></form>`))
	}))
	t.Cleanup(antiga.Close)
	if pageIsOurs(antiga.URL + "/") {
		t.Fatal("nao devia reabrir uma pagina antiga")
	}
}

func TestSairEncerraServidor(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	server := &http.Server{ReadHeaderTimeout: 5 * time.Second}
	server.Handler = newMux(func() {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()
		_ = server.Shutdown(ctx)
	})
	done := make(chan error, 1)
	go func() {
		err := server.Serve(ln)
		if err == http.ErrServerClosed {
			err = nil
		}
		done <- err
	}()

	resp, err := http.Post("http://"+ln.Addr().String()+"/api/sair", "application/json", nil)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("estado = %d", resp.StatusCode)
	}

	select {
	case err := <-done:
		if err != nil {
			t.Fatal(err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("o programa nao fechou")
	}
}

func postCompare(t *testing.T, first, second string) *httptest.ResponseRecorder {
	t.Helper()
	payload, err := json.Marshal(compareRequest{Codigo1: first, Codigo2: second})
	if err != nil {
		t.Fatal(err)
	}
	req := httptest.NewRequest(http.MethodPost, "/api/comparar", bytes.NewReader(payload))
	rec := httptest.NewRecorder()
	newMux(nil).ServeHTTP(rec, req)
	return rec
}

func decodeCompare(t *testing.T, rec *httptest.ResponseRecorder) compareResponse {
	t.Helper()
	var resp compareResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatal(err)
	}
	return resp
}
