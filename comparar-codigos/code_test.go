package main

import (
	"strings"
	"testing"
)

func TestParseValidCode(t *testing.T) {
	code, err := Parse("  1#12345671234567890  ")
	if err != nil {
		t.Fatal(err)
	}
	if code.Raw != "1#12345671234567890" {
		t.Fatalf("raw = %q", code.Raw)
	}
	if code.S != "1234567" {
		t.Fatalf("S = %q", code.S)
	}
	if code.P != "1234567890" {
		t.Fatalf("P = %q", code.P)
	}
}

func TestParseRejectsBadCodes(t *testing.T) {
	samples := []string{
		"",
		"1#",
		"12345671234567890",
		"2#12345671234567890",
		"1#1234567123456789",
		"1#123456712345678901",
		"1#123456A1234567890",
		"1#1234567 1234567890",
		"1#1234567123456789O",
	}
	for _, sample := range samples {
		if _, err := Parse(sample); err == nil {
			t.Fatalf("esperava erro para %q", sample)
		}
	}
}

func TestCompareKeepsLeadingZeros(t *testing.T) {
	left, err := Parse("1#00000010000000001")
	if err != nil {
		t.Fatal(err)
	}
	right, err := Parse("1#00000010000000001")
	if err != nil {
		t.Fatal(err)
	}
	result := Compare(left, right)
	if !result.Equal() {
		t.Fatalf("os mesmos digitos deviam ser iguais: %+v", result)
	}

	other, err := Parse("1#00000020000000001")
	if err != nil {
		t.Fatal(err)
	}
	result = Compare(left, other)
	if result.SEqual || !result.PEqual || result.Equal() {
		t.Fatalf("so o S devia diferir: %+v", result)
	}

	sameS, err := Parse("1#00000019999999999")
	if err != nil {
		t.Fatal(err)
	}
	result = Compare(left, sameS)
	if !result.Equal() || !result.SEqual || result.PEqual {
		t.Fatalf("o S igual devia chegar, mesmo com P diferente: %+v", result)
	}
}

func TestReport(t *testing.T) {
	left, err := Parse("1#12345671234567890")
	if err != nil {
		t.Fatal(err)
	}
	same, err := Parse("1#12345671234567890")
	if err != nil {
		t.Fatal(err)
	}
	text := Report(Compare(left, same))
	if !containsAll(text, "IGUAIS", "1234567 igual a 1234567") {
		t.Fatalf("relatorio inesperado:\n%s", text)
	}

	otherP, err := Parse("1#12345679999999999")
	if err != nil {
		t.Fatal(err)
	}
	text = Report(Compare(left, otherP))
	if !containsAll(text, "IGUAIS", "1234567 igual a 1234567") || strings.Contains(text, "DIFERENTES") || strings.Contains(text, "Numero P") {
		t.Fatalf("o P diferente nao devia mudar o resultado:\n%s", text)
	}

	otherS, err := Parse("1#76543211234567890")
	if err != nil {
		t.Fatal(err)
	}
	text = Report(Compare(left, otherS))
	if !containsAll(text, "DIFERENTES", "1234567 diferente de 7654321") {
		t.Fatalf("relatorio inesperado:\n%s", text)
	}
}

func containsAll(text string, parts ...string) bool {
	for _, part := range parts {
		if !strings.Contains(text, part) {
			return false
		}
	}
	return true
}
