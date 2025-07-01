docker build --no-cache -t multi-service-app .

docker run -d --rm -p 8080:8080 --name multi-service-app multi-service-app

curl -F "file=@/tmp/nginx.conf" http://localhost:8080/scan
