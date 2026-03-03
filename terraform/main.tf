provider "aws" {
  region = "eu-central-1"
}

# Recupera il tuo IP per la sicurezza
data "http" "mio_ip" {
  url = "http://ipv4.icanhazip.com"
}

resource "aws_default_vpc" "default" {}


resource "aws_security_group" "ml_server_sg" {
  name        = "ml-server-security-group"
  description = "Accesso SSH e MQTT per progetto ML"
  vpc_id      = aws_default_vpc.default.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["${chomp(data.http.mio_ip.response_body)}/32"]
  }


  ingress {
    description = "MQTT Broker"
    from_port   = 1883
    to_port     = 1883
    protocol    = "tcp"
    cidr_blocks = ["${chomp(data.http.mio_ip.response_body)}/32"] 
  }

  ingress {
    description = "API Monitoring"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] 
  }

  ingress {
    description = "Monitoring Frontend"
    from_port   = 3001
    to_port     = 3001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] 
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "ml_server" {
  ami           = "ami-0084a47cc718c111a" # Ubuntu 22.04
  instance_type = "t3.micro" 
  key_name      = "ml-server-key"

  root_block_device {
    volume_size = 20 
    volume_type = "gp3"
  }

  vpc_security_group_ids = [aws_security_group.ml_server_sg.id]

  user_data = <<-EOF
              #!/bin/bash
              # 1. Ottimizzazione memoria (Swap)
              fallocate -l 2G /swapfile
              chmod 600 /swapfile
              mkswap /swapfile
              swapon /swapfile
              echo '/swapfile none swap sw 0 0' >> /etc/fstab

              # 2. Installazione Docker e Docker Compose
              apt-get update
              apt-get install -y docker.io docker-compose
              systemctl start docker
              systemctl enable docker
              usermod -aG docker ubuntu

              echo "Server ML pronto con Docker" > /home/ubuntu/setup_completato.txt
              EOF

  tags = {
    Name = "ML-IoT-Server"
  }
}

output "ip_pubblico" {
  value = aws_instance.ml_server.public_ip
}

output "comando_ssh" {
  value = "ssh -i ml-server-key.pem ubuntu@${aws_instance.ml_server.public_ip}"
}
