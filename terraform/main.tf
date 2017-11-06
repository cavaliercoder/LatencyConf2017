provider "aws" {
  region = "ap-southeast-2"
}

data "aws_ami" "centos" {
  owners      = ["679593333241"]
  most_recent = true

  filter {
    name   = "name"
    values = ["CentOS Linux 7 x86_64 HVM EBS *"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }
}

resource "aws_key_pair" "demo" {
  key_name_prefix = "latency-"
  public_key      = "${file("~/.ssh/id_rsa.pub")}"
}

resource "aws_security_group" "demo" {
  name_prefix = "LatencyConf2017Demo"
  description = "Allow all inbound SSH and HTTP traffic"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_instance" "demo" {
  count           = 5
  ami             = "${data.aws_ami.centos.id}"
  instance_type   = "t2.micro"
  key_name        = "${aws_key_pair.demo.key_name}"
  security_groups = ["${aws_security_group.demo.name}"]

  user_data = <<EOF
#!/bin/sh
yum install -y http://cdn.cavaliercoder.com/LatencyConf2017/latencyd-1.0.0-1.el7.x86_64.rpm
systemctl enable latencyd
systemctl start latencyd
EOF

  tags {
    Environment = "demo"
    Name        = "LatencyConf2017-${count.index+1}"
  }
}

output "README" {
  value = <<EOF
EC2 Instances:

       Demo01:  ${element(aws_instance.demo.*.id, 0)} (${element(aws_instance.demo.*.public_ip, 0)})
       Demo02:  ${element(aws_instance.demo.*.id, 1)} (${element(aws_instance.demo.*.public_ip, 1)})
       Demo03:  ${element(aws_instance.demo.*.id, 2)} (${element(aws_instance.demo.*.public_ip, 2)})
       Demo04:  ${element(aws_instance.demo.*.id, 3)} (${element(aws_instance.demo.*.public_ip, 3)})
       Demo05:  ${element(aws_instance.demo.*.id, 4)} (${element(aws_instance.demo.*.public_ip, 4)})

EOF
}
