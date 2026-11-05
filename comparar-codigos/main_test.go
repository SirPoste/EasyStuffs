package main

import (
	"bytes"
	"strings"
	"testing"
)

func TestRunCommandLineEqual(t *testing.T) {
	var out, err bytes.Buffer
	code := run("comparar-codigos", []string{"1#12345671234567890", "1#12345671234567890"}, strings.NewReader(""), &out, &err)
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

func TestRunCommandLineDifferent(t *testing.T) {
	var out, err bytes.Buffer
	code := run("comparar-codigos", []string{"1#12345671234567890", "1#76543211234567890"}, strings.NewReader(""), &out, &err)
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
	code := run("comparar-codigos", []string{"1#12345671234567890", "123"}, strings.NewReader(""), &out, &err)
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
	code := run("comparar-codigos.exe", []string{"so-um"}, strings.NewReader(""), &out, &err)
	if code != 1 {
		t.Fatalf("saida = %d", code)
	}
	if !strings.Contains(err.String(), "Uso: comparar-codigos.exe <codigo1> <codigo2>") {
		t.Fatalf("stderr = %s", err.String())
	}
}

func TestRunInteractivePairThenExit(t *testing.T) {
	input := strings.NewReader("1#00000010000000001\n1#00000010000000002\n\n")
	var out, err bytes.Buffer
	code := run("comparar-codigos", nil, input, &out, &err)
	if code != 0 {
		t.Fatalf("saida = %d, stderr = %s", code, err.String())
	}
	text := out.String()
	if !strings.Contains(text, "0000001 igual a 0000001") {
		t.Fatalf("stdout = %s", text)
	}
	if !strings.Contains(text, "0000000001 diferente de 0000000002") {
		t.Fatalf("stdout = %s", text)
	}
	if !strings.Contains(text, "Resultado: DIFERENTES") {
		t.Fatalf("stdout = %s", text)
	}
}

func TestRunInteractiveInvalidThenAnotherPair(t *testing.T) {
	input := strings.NewReader("errado\n1#12345671234567890\n1#12345671234567890\n1#12345671234567890\n")
	var out, err bytes.Buffer
	code := run("comparar-codigos", nil, input, &out, &err)
	if code != 0 {
		t.Fatalf("saida = %d", code)
	}
	if !strings.Contains(err.String(), "codigo 1") {
		t.Fatalf("stderr = %s", err.String())
	}
	if !strings.Contains(out.String(), "Resultado: IGUAIS") {
		t.Fatalf("stdout = %s", out.String())
	}
}
