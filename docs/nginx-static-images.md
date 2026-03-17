# Nginx Static Image Configuration

This project publishes task images into `PUBLIC_IMAGE_DIR` and expects your
existing Nginx to serve that directory as public static files.

## Required .env values

Example:

```env
PUBLIC_IMAGE_DIR=./public-images
PUBLIC_IMAGE_BASE_URL=https://img.example.com/zip2telegraph
HOST_PUBLIC_IMAGE_DIR=/opt/zip2telegraph-public-images
```

`PUBLIC_IMAGE_DIR` is the container-internal path used by the bot.

`HOST_PUBLIC_IMAGE_DIR` is the host-side path used by Docker bind mounting.

With the example above, the bot writes files into the container at:

```text
/app/public-images
```

and Nginx should serve files from the host at:

```text
/opt/zip2telegraph-public-images
```

Telegraph pages will then reference URLs like:

```text
https://img.example.com/zip2telegraph/<task_id>/0001-image.png
```

## Recommended Nginx server block

If you already have a dedicated image subdomain:

```nginx
server {
    listen 80;
    server_name img.example.com;

    location /zip2telegraph/ {
        alias /opt/zip2telegraph-public-images/;
        autoindex off;
        add_header Cache-Control "public, max-age=31536000, immutable";
        try_files $uri =404;
    }
}
```

A ready-to-copy template file is included at:

`deploy/nginx/zip2telegraph-images.conf.example`

If your existing TLS setup is already managed elsewhere, apply the same path on
the `443` server block instead of creating a new plain HTTP server.

## Mapping rules

- `PUBLIC_IMAGE_BASE_URL` path must match the Nginx location path
- The Nginx `alias` path must point at `HOST_PUBLIC_IMAGE_DIR`
- Trailing slash matters: keep it on the `alias` path

For the example above:

- `PUBLIC_IMAGE_BASE_URL=https://img.example.com/zip2telegraph`
- `location /zip2telegraph/`
- `alias /opt/zip2telegraph-public-images/;`

## Verification

After deployment, check that files appear in:

```bash
ls -la /opt/zip2telegraph-public-images
```

Then open one of the generated URLs directly in your browser or with `curl`:

```bash
curl -I https://img.example.com/zip2telegraph/<task_id>/0001-image.png
```

You should receive `HTTP 200`.
