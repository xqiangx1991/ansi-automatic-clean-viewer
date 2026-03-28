#!/usr/bin/env python3
import json
import mimetypes
import os
from pathlib import Path
from xml.sax.saxutils import escape
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_JSON = ROOT / "package.json"
OUT_DIR = ROOT / "dist"


MIME_BY_EXT = {
    ".js": "application/javascript",
    ".json": "application/json",
    ".md": "text/markdown",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".txt": "text/plain",
    ".xml": "text/xml",
    ".vsixmanifest": "text/xml",
}

EXCLUDE_DIRS = {".git", ".github", ".vscode-test", "node_modules", "dist"}
EXCLUDE_FILES = {"tools/build_vsix.py"}


def iter_extension_files(root: Path):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for name in files:
            rel = Path(base, name).relative_to(root).as_posix()
            if rel in EXCLUDE_FILES:
                continue
            yield rel


def content_type_for(path: str):
    ext = Path(path).suffix.lower()
    if ext in MIME_BY_EXT:
        return MIME_BY_EXT[ext]
    guessed = mimetypes.types_map.get(ext)
    return guessed or "application/octet-stream"


def build_manifest(pkg: dict) -> str:
    display_name = escape(pkg.get("displayName", pkg["name"]))
    description = escape(pkg.get("description", ""))
    tags = escape(",".join(pkg.get("keywords", [])))
    categories = escape(",".join(pkg.get("categories", [])))
    publisher = escape(pkg["publisher"])
    name = escape(pkg["name"])
    version = escape(pkg["version"])
    engine = escape(pkg.get("engines", {}).get("vscode", ""))

    assets = [
        '<Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />'
    ]
    if (ROOT / "README.md").exists():
        assets.append(
            '<Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/README.md" Addressable="true" />'
        )
    if (ROOT / "LICENSE").exists():
        assets.append(
            '<Asset Type="Microsoft.VisualStudio.Services.Content.License" Path="extension/LICENSE" Addressable="true" />'
        )
    if (ROOT / "icon.png").exists():
        assets.append(
            '<Asset Type="Microsoft.VisualStudio.Services.Icons.Default" Path="extension/icon.png" Addressable="true" />'
        )

    return f"""<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="{name}" Version="{version}" Publisher="{publisher}" />
    <DisplayName>{display_name}</DisplayName>
    <Description xml:space="preserve">{description}</Description>
    <Tags>{tags}</Tags>
    <Categories>{categories}</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="{engine}" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionPack" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.LocalizedLanguages" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.PreRelease" Value="false" />
    </Properties>
    <License>extension/LICENSE</License>
    <Icon>extension/icon.png</Icon>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code" />
  </Installation>
  <Dependencies />
  <Assets>
    {"".join(assets)}
  </Assets>
</PackageManifest>
"""


def build_content_types(files):
    exts = {Path(p).suffix.lower() for p in files if Path(p).suffix}
    exts.add(".vsixmanifest")
    lines = ['<?xml version="1.0" encoding="utf-8"?>']
    lines.append('<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">')
    for ext in sorted(exts):
        ctype = content_type_for("x" + ext)
        lines.append(f'  <Default Extension="{ext}" ContentType="{ctype}" />')
    lines.append("</Types>")
    return "\n".join(lines) + "\n"


def main():
    pkg = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    files = sorted(iter_extension_files(ROOT))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    vsix_name = f'{pkg["name"]}-{pkg["version"]}.vsix'
    out_path = OUT_DIR / vsix_name

    manifest = build_manifest(pkg)
    content_types = build_content_types(files)

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("extension.vsixmanifest", manifest)
        zf.writestr("[Content_Types].xml", content_types)
        for rel in files:
            zf.write(ROOT / rel, f"extension/{rel}")

    print(out_path)


if __name__ == "__main__":
    main()
