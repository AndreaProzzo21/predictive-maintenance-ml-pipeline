FROM node:18-alpine

WORKDIR /app

# Installiamo le dipendenze separatamente per sfruttare la cache di Docker
COPY package.json ./
RUN npm install

# Copiamo il resto del codice
COPY . .

EXPOSE 3000

# Per React in Docker locale è spesso necessario questo flag per l'hot reload
ENV CHOKIDAR_USEPOLLING=true

CMD ["npm", "start"]