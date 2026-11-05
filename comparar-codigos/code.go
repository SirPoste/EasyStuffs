package main

import (
	"fmt"
	"strings"
)

const (
	codePrefix = "1#"
	sDigits    = 7
	pDigits    = 10
)

// ErrFormat is returned when a reading does not match 1# + 7 digits + 10 digits.
var ErrFormat = fmt.Errorf("formato invalido: esperado %s seguido de %d digitos e %d digitos", codePrefix, sDigits, pDigits)

// Code is one barcode in the form 1#SSSSSSSPPPPPPPPPP.
type Code struct {
	Raw string
	S   string
	P   string
}

// Result is the comparison of two codes. The decision uses only S.
type Result struct {
	Left   Code
	Right  Code
	SEqual bool
	PEqual bool
}

// Equal reports whether the S numbers match. P is ignored.
func (r Result) Equal() bool {
	return r.SEqual
}

// Parse reads one barcode. Spaces around the reading are ignored.
// The digits are kept as text, so leading zeros stay significant.
func Parse(raw string) (Code, error) {
	s := strings.TrimSpace(raw)
	rest, ok := strings.CutPrefix(s, codePrefix)
	if !ok || len(rest) != sDigits+pDigits || !digits(rest) {
		return Code{}, ErrFormat
	}
	return Code{Raw: s, S: rest[:sDigits], P: rest[sDigits:]}, nil
}

// Compare checks the S number and the P number of two codes.
func Compare(left, right Code) Result {
	return Result{
		Left:   left,
		Right:  right,
		SEqual: left.S == right.S,
		PEqual: left.P == right.P,
	}
}

// Report is the text shown after a valid pair of readings.
func Report(r Result) string {
	outcome := "DIFERENTES"
	if r.Equal() {
		outcome = "IGUAIS"
	}
	return fmt.Sprintf(
		"Codigo 1: %s\nCodigo 2: %s\nNumero S: %s %s %s\nResultado: %s\n",
		r.Left.Raw, r.Right.Raw,
		r.Left.S, relation(r.SEqual), r.Right.S,
		outcome,
	)
}

func relation(equal bool) string {
	if equal {
		return "igual a"
	}
	return "diferente de"
}

func digits(s string) bool {
	for _, r := range s {
		if r < '0' || r > '9' {
			return false
		}
	}
	return s != ""
}
