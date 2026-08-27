package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

var imageExts = map[string]bool{
	".jpg":  true,
	".jpeg": true,
	".png":  true,
	".gif":  true,
	".bmp":  true,
	".webp": true,
	".tif":  true,
	".tiff": true,
	".svg":  true,
	".ico":  true,
	".jfif": true,
	".heic": true,
	".heif": true,
	".avif": true,
}

var skipDirNames = map[string]bool{
	"update":        true,
	".git":          true,
	".svn":          true,
	".hg":           true,
	"node_modules":  true,
	"__macosx":      true,
	"system volume information": true,
}

const updateDirName = "update"

// ModeAll copies every source image into every target folder (overwrite if present).
// ModeExisting only overwrites files that already exist with the same name.
type Mode string

const (
	ModeAll      Mode = "all"
	ModeExisting Mode = "existing"
)

type Options struct {
	Root string
	Mode Mode
}

type FileOp struct {
	Source      string
	Destination string
	Action      string // copied, updated, skipped
}

type Result struct {
	SourceImages int
	TargetDirs   int
	Copied       int
	Updated      int
	Skipped      int
	Ops          []FileOp
	Warnings     []string
	Errors       []string
}

type sourceImage struct {
	Name string
	Path string
	Hash string
	Size int64
}

func SyncImages(opts Options) (Result, error) {
	var res Result

	root, err := filepath.Abs(opts.Root)
	if err != nil {
		return res, fmt.Errorf("pasta raiz invalida: %w", err)
	}
	info, err := os.Stat(root)
	if err != nil {
		return res, fmt.Errorf("nao foi possivel abrir a pasta raiz: %w", err)
	}
	if !info.IsDir() {
		return res, fmt.Errorf("a raiz nao e uma pasta: %s", root)
	}

	mode := opts.Mode
	if mode == "" {
		mode = ModeAll
	}
	if mode != ModeAll && mode != ModeExisting {
		return res, fmt.Errorf("modo desconhecido: %s", mode)
	}

	updateDir := filepath.Join(root, updateDirName)
	if st, err := os.Stat(updateDir); err != nil || !st.IsDir() {
		return res, fmt.Errorf("nao existe a pasta %q junto ao executavel", updateDirName)
	}

	sources, warnings, err := collectSources(updateDir)
	if err != nil {
		return res, err
	}
	res.Warnings = append(res.Warnings, warnings...)
	res.SourceImages = len(sources)
	if len(sources) == 0 {
		return res, fmt.Errorf("a pasta %q nao contem imagens", updateDirName)
	}

	targets, err := collectTargetDirs(root)
	if err != nil {
		return res, err
	}
	res.TargetDirs = len(targets)
	if len(targets) == 0 {
		return res, fmt.Errorf("nao foram encontradas pastas de destino")
	}

	for _, dir := range targets {
		entries, err := os.ReadDir(dir)
		if err != nil {
			res.Errors = append(res.Errors, fmt.Sprintf("nao foi possivel ler %s: %v", dir, err))
			continue
		}
		existing := map[string]string{}
		for _, e := range entries {
			if e.IsDir() {
				continue
			}
			existing[strings.ToLower(e.Name())] = e.Name()
		}

		for _, src := range sources {
			destName := src.Name
			if actual, ok := existing[strings.ToLower(src.Name)]; ok {
				destName = actual
			} else if mode == ModeExisting {
				continue
			}

			destPath := filepath.Join(dir, destName)
			op, err := copyIfNeeded(src, destPath, existing[strings.ToLower(src.Name)] != "")
			if err != nil {
				res.Errors = append(res.Errors, fmt.Sprintf("%s -> %s: %v", src.Name, destPath, err))
				continue
			}
			res.Ops = append(res.Ops, op)
			switch op.Action {
			case "copied":
				res.Copied++
			case "updated":
				res.Updated++
			case "skipped":
				res.Skipped++
			}
		}
	}

	return res, nil
}

func collectSources(updateDir string) ([]sourceImage, []string, error) {
	byName := map[string]sourceImage{}
	var warnings []string

	err := filepath.WalkDir(updateDir, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		if !isImage(d.Name()) {
			return nil
		}
		info, err := d.Info()
		if err != nil {
			return err
		}
		hash, err := fileHash(path)
		if err != nil {
			return fmt.Errorf("a ler %s: %w", path, err)
		}
		key := strings.ToLower(d.Name())
		if prev, ok := byName[key]; ok {
			warnings = append(warnings, fmt.Sprintf(
				"nome duplicado na pasta update: %s (a usar %s, ignorado %s)",
				d.Name(), prev.Path, path,
			))
			return nil
		}
		byName[key] = sourceImage{
			Name: d.Name(),
			Path: path,
			Hash: hash,
			Size: info.Size(),
		}
		return nil
	})
	if err != nil {
		return nil, warnings, err
	}

	names := make([]string, 0, len(byName))
	for k := range byName {
		names = append(names, k)
	}
	sort.Strings(names)
	out := make([]sourceImage, 0, len(names))
	for _, k := range names {
		out = append(out, byName[k])
	}
	return out, warnings, nil
}

func collectTargetDirs(root string) ([]string, error) {
	var dirs []string
	err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !d.IsDir() {
			return nil
		}
		name := strings.ToLower(d.Name())
		if path != root && skipDirNames[name] {
			return filepath.SkipDir
		}
		if path == root {
			return nil
		}
		if strings.HasPrefix(d.Name(), ".") {
			return filepath.SkipDir
		}
		dirs = append(dirs, path)
		return nil
	})
	if err != nil {
		return nil, err
	}
	sort.Strings(dirs)
	return dirs, nil
}

func copyIfNeeded(src sourceImage, destPath string, existed bool) (FileOp, error) {
	op := FileOp{Source: src.Path, Destination: destPath}

	if existed {
		st, err := os.Stat(destPath)
		if err == nil && st.Size() == src.Size {
			destHash, err := fileHash(destPath)
			if err == nil && destHash == src.Hash {
				op.Action = "skipped"
				return op, nil
			}
		}
	}

	if err := copyFile(src.Path, destPath); err != nil {
		return op, err
	}
	if existed {
		op.Action = "updated"
	} else {
		op.Action = "copied"
	}
	return op, nil
}

func copyFile(src, dest string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	tmp := dest + ".tmp-image-updater"
	out, err := os.OpenFile(tmp, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
	if err != nil {
		return err
	}
	_, copyErr := io.Copy(out, in)
	closeErr := out.Close()
	if copyErr != nil {
		os.Remove(tmp)
		return copyErr
	}
	if closeErr != nil {
		os.Remove(tmp)
		return closeErr
	}
	if err := os.Rename(tmp, dest); err != nil {
		os.Remove(tmp)
		return err
	}
	return nil
}

func fileHash(path string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()
	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", err
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

func isImage(name string) bool {
	return imageExts[strings.ToLower(filepath.Ext(name))]
}
