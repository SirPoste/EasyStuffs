package main

import (
	"os"
	"path/filepath"
	"testing"
)

var (
	pngA = []byte{
		0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d,
		0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
		0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xde, 0x00, 0x00, 0x00,
		0x0c, 0x49, 0x44, 0x41, 0x54, 0x08, 0xd7, 0x63, 0xf8, 0xcf, 0xc0, 0x00,
		0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x05, 0xfe, 0xd4, 0xef, 0x00, 0x00,
		0x00, 0x00, 0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82,
	}
	pngB = []byte{
		0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d,
		0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
		0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xde, 0x00, 0x00, 0x00,
		0x0c, 0x49, 0x44, 0x41, 0x54, 0x08, 0xd7, 0x63, 0x10, 0x01, 0x01, 0x00,
		0x00, 0x00, 0x03, 0x00, 0x01, 0x6d, 0xbd, 0xa7, 0xba, 0x00, 0x00, 0x00,
		0x00, 0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82,
	}
)

func writeFile(t *testing.T, path string, data []byte) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, data, 0644); err != nil {
		t.Fatal(err)
	}
}

func readFile(t *testing.T, path string) []byte {
	t.Helper()
	b, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return b
}

func setupTree(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	writeFile(t, filepath.Join(root, "update", "logo.png"), pngB)
	writeFile(t, filepath.Join(root, "update", "nova.jpg"), pngB)
	writeFile(t, filepath.Join(root, "loja-a", "logo.png"), pngA)
	writeFile(t, filepath.Join(root, "loja-a", "outro.txt"), []byte("keep"))
	writeFile(t, filepath.Join(root, "loja-b", "produtos", "logo.png"), pngA)
	if err := os.MkdirAll(filepath.Join(root, "loja-c", "vazia"), 0755); err != nil {
		t.Fatal(err)
	}
	return root
}

func TestSyncAllCopiesAndUpdatesEverywhere(t *testing.T) {
	root := setupTree(t)
	res, err := SyncImages(Options{Root: root, Mode: ModeAll})
	if err != nil {
		t.Fatal(err)
	}
	if res.SourceImages != 2 {
		t.Fatalf("source images = %d, want 2", res.SourceImages)
	}
	if res.Updated < 2 {
		t.Fatalf("updated = %d, want at least 2 (logo.png in loja-a and loja-b/produtos)", res.Updated)
	}
	if res.Copied < 1 {
		t.Fatalf("copied = %d, want new files in folders that lacked them", res.Copied)
	}

	if got := readFile(t, filepath.Join(root, "loja-a", "logo.png")); string(got) != string(pngB) {
		t.Fatal("loja-a/logo.png was not updated")
	}
	if got := readFile(t, filepath.Join(root, "loja-b", "produtos", "logo.png")); string(got) != string(pngB) {
		t.Fatal("loja-b/produtos/logo.png was not updated")
	}
	if _, err := os.Stat(filepath.Join(root, "loja-a", "nova.jpg")); err != nil {
		t.Fatal("expected nova.jpg to be imported into loja-a")
	}
	if _, err := os.Stat(filepath.Join(root, "loja-c", "vazia", "logo.png")); err != nil {
		t.Fatal("expected images in nested empty folder")
	}
	if _, err := os.Stat(filepath.Join(root, "loja-c", "logo.png")); err != nil {
		t.Fatal("expected images in loja-c")
	}
	if got := readFile(t, filepath.Join(root, "loja-a", "outro.txt")); string(got) != "keep" {
		t.Fatal("non-image file should not be touched")
	}
	if _, err := os.Stat(filepath.Join(root, "logo.png")); err == nil {
		t.Fatal("should not copy images into the root next to the exe")
	}
}

func TestSyncExistingOnlyReplacesMatchingNames(t *testing.T) {
	root := setupTree(t)
	res, err := SyncImages(Options{Root: root, Mode: ModeExisting})
	if err != nil {
		t.Fatal(err)
	}
	if res.Copied != 0 {
		t.Fatalf("copied = %d, want 0 in existing mode", res.Copied)
	}
	if res.Updated != 2 {
		t.Fatalf("updated = %d, want 2", res.Updated)
	}
	if _, err := os.Stat(filepath.Join(root, "loja-a", "nova.jpg")); err == nil {
		t.Fatal("existing mode must not import new filenames")
	}
	if _, err := os.Stat(filepath.Join(root, "loja-c", "logo.png")); err == nil {
		t.Fatal("existing mode must not create files in empty folders")
	}
	if got := readFile(t, filepath.Join(root, "loja-a", "logo.png")); string(got) != string(pngB) {
		t.Fatal("matching file should still be updated")
	}
}

func TestSkipIdentical(t *testing.T) {
	root := t.TempDir()
	writeFile(t, filepath.Join(root, "update", "logo.png"), pngB)
	writeFile(t, filepath.Join(root, "dest", "logo.png"), pngB)
	res, err := SyncImages(Options{Root: root, Mode: ModeExisting})
	if err != nil {
		t.Fatal(err)
	}
	if res.Skipped != 1 || res.Updated != 0 || res.Copied != 0 {
		t.Fatalf("got copied=%d updated=%d skipped=%d, want skipped=1", res.Copied, res.Updated, res.Skipped)
	}
}

func TestMissingUpdateFolder(t *testing.T) {
	root := t.TempDir()
	_, err := SyncImages(Options{Root: root, Mode: ModeAll})
	if err == nil {
		t.Fatal("expected error when update folder is missing")
	}
}

func TestDoesNotWriteIntoUpdateFolder(t *testing.T) {
	root := t.TempDir()
	writeFile(t, filepath.Join(root, "update", "logo.png"), pngB)
	writeFile(t, filepath.Join(root, "update", "nested", "keep.png"), pngA)
	writeFile(t, filepath.Join(root, "dest", "x.txt"), []byte("x"))
	_, err := SyncImages(Options{Root: root, Mode: ModeAll})
	if err != nil {
		t.Fatal(err)
	}
	if got := readFile(t, filepath.Join(root, "update", "nested", "keep.png")); string(got) != string(pngA) {
		t.Fatal("files inside update/ must not be overwritten by the sync")
	}
}

func TestSkipsDotAndGitFolders(t *testing.T) {
	root := t.TempDir()
	writeFile(t, filepath.Join(root, "update", "logo.png"), pngB)
	writeFile(t, filepath.Join(root, ".hidden", "old.png"), pngA)
	writeFile(t, filepath.Join(root, ".git", "old.png"), pngA)
	writeFile(t, filepath.Join(root, "ok", "old.png"), pngA)
	_, err := SyncImages(Options{Root: root, Mode: ModeAll})
	if err != nil {
		t.Fatal(err)
	}
	if got := readFile(t, filepath.Join(root, ".hidden", "old.png")); string(got) != string(pngA) {
		t.Fatal(".hidden should be skipped")
	}
	if got := readFile(t, filepath.Join(root, ".git", "old.png")); string(got) != string(pngA) {
		t.Fatal(".git should be skipped")
	}
	if _, err := os.Stat(filepath.Join(root, "ok", "logo.png")); err != nil {
		t.Fatal("normal folder should receive the image")
	}
}

func TestWriteLogGoesToUpdateFolder(t *testing.T) {
	root := t.TempDir()
	writeFile(t, filepath.Join(root, "update", "logo.png"), pngB)
	writeFile(t, filepath.Join(root, "dest", "keep.txt"), []byte("x"))

	res, err := SyncImages(Options{Root: root, Mode: ModeAll})
	if err != nil {
		t.Fatal(err)
	}
	writeLog(root, res)

	path := filepath.Join(root, "update", "atualizacao-imagens.log")
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("expected log at %s: %v", path, err)
	}
	if _, err := os.Stat(filepath.Join(root, "atualizacao-imagens.log")); err == nil {
		t.Fatal("log must not be written to the root")
	}
	if _, err := os.Stat(filepath.Join(root, "dest", "atualizacao-imagens.log")); err == nil {
		t.Fatal("log must not be copied to target folders")
	}
}
