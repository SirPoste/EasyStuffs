package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestIndexPage(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	rec := httptest.NewRecorder()
	newMux().ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("estado = %d", rec.Code)
	}
	body := rec.Body.String()
	if !strings.Contains(body, `aria-label="Audi"`) {
		t.Fatal("a pagina devia ter o logotipo da Audi")
	}
	if !strings.Contains(body, "Primeiro código") || !strings.Contains(body, "Segundo código") {
		t.Fatal("faltam os campos de leitura")
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

func postCompare(t *testing.T, first, second string) *httptest.ResponseRecorder {
	t.Helper()
	payload, err := json.Marshal(compareRequest{Codigo1: first, Codigo2: second})
	if err != nil {
		t.Fatal(err)
	}
	req := httptest.NewRequest(http.MethodPost, "/api/comparar", bytes.NewReader(payload))
	rec := httptest.NewRecorder()
	newMux().ServeHTTP(rec, req)
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
