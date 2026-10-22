# Third-party assets and license scope

The [repository MIT license](LICENSE) covers this project's original code
and documentation. It does not relicense third-party model assets or
publisher-supplied configuration.

## Microsoft MAI Code 1.1 Flash On-Device package

Publisher: Microsoft. Distribution source: Azure Machine Learning (Azure ML)
public model catalog. The asset below is the quantized on-device GGUF
variant, with `Q2-XS` in the main filename, not the full-precision checkpoint.

```text
azureml://registries/azureml/models/MAI-Code-1.1-Flash-On-Device/versions/2
```

| Asset | Relationship to this repository |
|---|---|
| `MAI-Code-1.1-Flash-Q2-XS.gguf` | Quantized on-device model weights fetched directly from the publisher's Azure ML download location; not included in this repository. |
| `dflash-v3-lc1.gguf` | Drafter weights fetched from the same package; not included in this repository. |
| [`configs/llama-config.json`](configs/llama-config.json) | Publisher-supplied configuration included as a reference copy, not original project code. |

The Azure ML metadata for this asset reports `MIT` as its license as of
October 22, 2026. That is upstream licensing information, independent of
this project's MIT license; this repository does not issue its own license
grant for those assets.

Review the [publisher's model card](https://github.com/Azure/azureml-assets/wiki/models-MAI-Code-1.1-Flash-On-Device),
the license information in the [Azure ML asset listing](https://ml.azure.com/registries/azureml/models/MAI-Code-1.1-Flash-On-Device/version/2),
and any license files, notices and applicable terms supplied with the assets.
Do not treat a catalog license label or this notice as a replacement for
the full upstream terms.

Use, modification and redistribution of those assets must comply with their
applicable licenses, required notices, restrictions and download/use terms.
Preserve notices as required by the applicable upstream license. Neither
using the downloader nor downloading manually changes those obligations,
and this project's MIT license does not override them or grant additional
rights in third-party assets.
