# Assets estaticos de la Boveda

Este directorio contiene los archivos reales que la Boveda Forense puede ofrecer para descarga.

## Convencion de ubicacion

- Carpeta por caso: `backend/assets/<case_id>/`
- Nombre de archivo: por defecto debe coincidir con `vault_evidence.<codigo>.title` del JSON del caso

Ejemplos:

- `backend/assets/martes_3/club_fotos_originales.zip`
- `backend/assets/grabacion_1/audios_ana_campo.zip`

## Como resuelve archivos el backend

El endpoint `POST /api/v1/vault/unlock` busca, en este orden:

1. `file_path` dentro de la evidencia del JSON, si existiera en el futuro.
2. `file_name` dentro de la evidencia del JSON, si existiera en el futuro.
3. `title` como nombre de archivo dentro de `backend/assets/<case_id>/`.

Si el archivo existe en disco, la respuesta incluye `file_url`.
Si no existe, la evidencia sigue desbloqueandose pero solo devuelve metadata.

## Que debe subir el propietario

Subir aqui los archivos definitivos de evidencia:

- PDFs
- ZIPs
- imagenes
- audios

No generar estos archivos con IA dentro del repo. El contenido lo provee el propietario/guionista.

## Estructura inicial

- `postuma_0/`
- `grabacion_1/`
- `herencia_2/`
- `martes_3/`
- `novia_4/`
- `experimento_5/`
- `caso_cero/`
