docker build -t link-quick-start .
docker run --env-file .env -p 3000:3000 -it link-quick-start
