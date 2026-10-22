# Download without the Python script

The files are served by Azure Blob Storage, not bundled in this repository.
You can resolve a temporary download location and then use curl, a browser
or a download manager. No Azure account, Azure CLI or Python is required.

The flow is:

1. Resolve the pinned Azure ML asset ID.
2. Read `blobSasUri` from the JSON response.
3. Insert each filename into that Blob URL's path, leaving its signed query
   string unchanged.
4. Download the three files and compare their sizes/checksums with
   [the model details](model-and-runtime.md).

The signed location expires. Do not save it in this repo, paste it into an
issue or share it in screenshots. Resolve a fresh location if it expires.
There is intentionally no hard-coded temporary download link here.

## 1. Resolve the package and inspect file sizes

The following PowerShell commands retrieve JSON and headers only, not model
or config file bodies:

```powershell
$assetId = 'azureml://registries/azureml/models/MAI-Code-1.1-Flash-On-Device/versions/2'
$endpoint = 'https://api.catalog.azureml.ms/modelregistry/v1.0/registry/models/nonazureaccount?assetId='
$resolved = Invoke-RestMethod -Uri ($endpoint + [uri]::EscapeDataString($assetId))
$blob = [uri]$resolved.blobSasUri
$base = $blob.GetLeftPart([System.UriPartial]::Path).TrimEnd('/')
$files = @('MAI-Code-1.1-Flash-Q2-XS.gguf', 'dflash-v3-lc1.gguf', 'llama-config.json')
$sizes = @{}

foreach ($name in $files) {
    $url = "$base/$([uri]::EscapeDataString($name))$($blob.Query)"
    $head = Invoke-WebRequest -Method Head -Uri $url -ErrorAction Stop
    $sizes[$name] = [long]($head.Headers['Content-Length'] | Select-Object -First 1)
    [pscustomobject]@{
        File = $name
        Bytes = $sizes[$name]
    }
}
```

`blobSasUri` is the package container/prefix, not the main GGUF file itself.
The filename belongs **before** the `?` query. Appending a filename after
the query, or dropping the query, does not produce a valid download URL.

If using a browser instead, open the resolver endpoint with the encoded
asset ID, inspect the JSON locally, and construct the file URLs using the
same path/query rule. These are signed Blob URLs, not Hugging Face URLs.

## 2. Download with curl

The following commands **do download files**. Run them only when you are
ready for the 56,688,835,352-byte package:

```powershell
$out = Join-Path (Get-Location) 'models\MAI-Code-1.1-Flash-On-Device'
New-Item -ItemType Directory -Path $out -Force | Out-Null

foreach ($name in $files) {
    $url = "$base/$([uri]::EscapeDataString($name))$($blob.Query)"
    $target = Join-Path $out $name
    if (Test-Path -LiteralPath $target) {
        $local = Get-Item -LiteralPath $target
        if ($local.PSIsContainer -or $local.Length -gt $sizes[$name]) {
            throw "Invalid existing destination for $name; it will not be overwritten."
        }
        if ($local.Length -eq $sizes[$name]) { continue }
    }
    curl.exe --fail --retry 3 --continue-at - --output $target $url
    if ($LASTEXITCODE -ne 0) {
        throw "Download failed for $name. Resolve a fresh location before retrying."
    }
}
```

This uses Windows `curl.exe`, not a PowerShell alias. On Linux/macOS use
`curl` and a destination path appropriate for that system. A single-file
command has this form; replace `FILE_URL` with the complete signed file URL:

```text
curl --fail --retry 3 --continue-at - --output MAI-Code-1.1-Flash-Q2-XS.gguf "FILE_URL"
```

`--continue-at -` resumes from the size of the destination file. After an
interruption, resolve a new location and rerun the download commands with
the same output directory. Only reuse partial files from this exact asset
version, and check the final checksum before loading the model.

These curl examples transfer one file at a time. They do not split the
large GGUF into concurrent ranges; use a download manager with that feature
or the Python downloader's `--parallelism` option if you want that behavior.
The curl files are independent of the Python downloader's `.part` journals.

## 3. Check the downloaded files

Expected sizes are 56,307,620,832 bytes for the main model, 381,214,016 bytes
for the drafter and 504 bytes for the config. To display SHA-256 values:

```powershell
foreach ($name in $files) {
    $path = Join-Path $out $name
    [pscustomobject]@{
        File = $name
        SHA256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}
```

Compare with [the reference values](model-and-runtime.md). Curl does not
perform these reference-checksum comparisons for you.

The downloaded `llama-config.json` names the model and drafter and provides
the publisher's serving settings. See [basic llama.cpp configuration](model-and-runtime.md)
for the reference copy and command-line equivalents.

The Python script automates the same resolver/Blob flow, adds bounded
parallel ranges and retries, checks file identities and verifies the
reference checksums. It is a convenience, not a requirement for access.

References: [Azure ML catalog API](https://api.catalog.azureml.ms/asset-gallery/v1.0),
[Azure Get Blob](https://learn.microsoft.com/en-us/rest/api/storageservices/get-blob),
and [curl options](https://curl.se/docs/manpage.html).
