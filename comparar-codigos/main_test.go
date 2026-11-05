package main

import (
	"bytes"
	"strings"
	"testing"
)

func TestRunCommandLineEqual(t *testing.T) {
	var out, err bytes.Buffer
	code := run("comparar-codigos", []string{"1#12345671234567890", "1#12345671234567890"}, &out, &err)
	if code != 0 {
		t.Fatalf("saida = %d, stderr = %s", code, err.String())
	}
	if !strings.Contains(out.String(), "Resultado: IGUAIS") {
		t.Fatalf("stdout = %s", out.String())
	}
	if err.Len() != 0 {
		t.Fatalf("stderr = %s", err.String())
	}
}

func TestRunCommandLineSameSDifferentP(t *testing.T) {
	var out, err bytes.Buffer
	code := run("comparar-codigos", []string{"1#12345671234567890", "1#12345670000000000"}, &out, &err)
	if code != 0 {
		t.Fatalf("saida = %d, stdout = %s, stderr = %s", code, out.String(), err.String())
	}
	if !strings.Contains(out.String(), "Numero S: 1234567 igual a 1234567") {
		t.Fatalf("stdout = %s", out.String())
	}
	if !strings.Contains(out.String(), "Resultado: IGUAIS") {
		t.Fatalf("stdout = %s", out.String())
	}
}

func TestRunCommandLineDifferent(t *testing.T) {
	var out, err bytes.Buffer
	code := run("comparar-codigos", []string{"1#12345671234567890", "1#76543211234567890"}, &out, &err)
	if code != 2 {
		t.Fatalf("saida = %d, stdout = %s, stderr = %s", code, out.String(), err.String())
	}
	if !strings.Contains(out.String(), "Resultado: DIFERENTES") {
		t.Fatalf("stdout = %s", out.String())
	}
	if !strings.Contains(out.String(), "1234567 diferente de 7654321") {
		t.Fatalf("stdout = %s", out.String())
	}
}

func TestRunCommandLineInvalidSecondCode(t *testing.T) {
	var out, err bytes.Buffer
	code := run("comparar-codigos", []string{"1#12345671234567890", "123"}, &out, &err)
	if code != 1 {
		t.Fatalf("saida = %d", code)
	}
	if !strings.Contains(err.String(), "codigo 2") {
		t.Fatalf("stderr = %s", err.String())
	}
	if out.Len() != 0 {
		t.Fatalf("nao devia haver relatorio: %s", out.String())
	}
}

func TestRunUsage(t *testing.T) {
	var out, err bytes.Buffer
	code := run("comparar-codigos.exe", []string{"so-um"}, &out, &err)
	if code != 1 {
		t.Fatalf("saida = %d", code)
	}
	if !strings.Contains(err.String(), "Uso: comparar-codigos.exe") {
		t.Fatalf("stderr = %s", err.String())
	}
	if !strings.Contains(err.String(), "abre a pagina") {
		t.Fatalf("stderr = %s", err.String())
	}
}
