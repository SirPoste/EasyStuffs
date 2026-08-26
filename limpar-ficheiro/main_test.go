package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestEmptyFileRemovesContent(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "save.dat")
	payload := []byte("dados secretos 123\x00\xff")
	if err := os.WriteFile(path, payload, 0o644); err != nil {
		t.Fatal(err)
	}

	if err := emptyFile(path); err != nil {
		t.Fatalf("emptyFile: %v", err)
	}

	info, err := os.Stat(path)
	if err != nil {
		t.Fatalf("ficheiro deveria continuar a existir: %v", err)
	}
	if info.Size() != 0 {
		t.Fatalf("tamanho = %d, queria 0", info.Size())
	}

	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(data) != 0 {
		t.Fatalf("conteudo restante: %q", data)
	}
}

func TestEmptyFileAlreadyEmpty(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "vazio.txt")
	if err := os.WriteFile(path, nil, 0o644); err != nil {
		t.Fatal(err)
	}
	if err := emptyFile(path); err != nil {
		t.Fatalf("emptyFile: %v", err)
	}
	info, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	if info.Size() != 0 {
		t.Fatalf("tamanho = %d, queria 0", info.Size())
	}
}

func TestEmptyFileMissing(t *testing.T) {
	err := emptyFile(filepath.Join(t.TempDir(), "nao-existe.dat"))
	if err == nil {
		t.Fatal("esperava erro para ficheiro inexistente")
	}
}

func TestEmptyFileRejectsDirectory(t *testing.T) {
	err := emptyFile(t.TempDir())
	if err == nil {
		t.Fatal("esperava erro para pasta")
	}
}

func TestEmptyFileRejectsSymlink(t *testing.T) {
	dir := t.TempDir()
	target := filepath.Join(dir, "alvo.dat")
	link := filepath.Join(dir, "atalho.dat")
	if err := os.WriteFile(target, []byte("conteudo"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(target, link); err != nil {
		t.Fatal(err)
	}

	if err := emptyFile(link); err == nil {
		t.Fatal("esperava recusar symlink")
	}

	data, err := os.ReadFile(target)
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != "conteudo" {
		t.Fatalf("o alvo do symlink nao deveria ser alterado: %q", data)
	}
}
