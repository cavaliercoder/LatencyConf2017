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

resource "aws_iam_role" "demo" {
  name_prefix = "LatencyConf2017Demo"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Principal": { "Service": "ec2.amazonaws.com" },
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_instance_profile" "demo" {
  name_prefix = "LatencyConf2017Demo"
  role        = "${aws_iam_role.demo.name}"
}

resource "aws_iam_policy" "demo" {
  name_prefix = "CloudWatchLogsWriteAccess"
  description = "Provides read only access to CloudWatch Logs"
  path        = "/"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
    ],
    "Resource": [ "arn:aws:logs:*:*:*" ]
  }
 ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "demo" {
  role       = "${aws_iam_role.demo.name}"
  policy_arn = "${aws_iam_policy.demo.id}"
}

resource "aws_instance" "demo" {
  count                = 10
  ami                  = "${data.aws_ami.centos.id}"
  instance_type        = "t2.micro"
  key_name             = "${aws_key_pair.demo.key_name}"
  security_groups      = ["${aws_security_group.demo.name}"]
  iam_instance_profile = "${aws_iam_instance_profile.demo.name}"

  tags {
    Name        = "node${count.index+1}"
    Description = "latencyconf.io"
    Environment = "latency-demo"
  }
}

output "README" {
  value = <<EOF
EC2 Instances:

       node1:   ${element(aws_instance.demo.*.id, 0)} (${element(aws_instance.demo.*.public_ip, 0)})
       node2:   ${element(aws_instance.demo.*.id, 1)} (${element(aws_instance.demo.*.public_ip, 1)})
       node3:   ${element(aws_instance.demo.*.id, 2)} (${element(aws_instance.demo.*.public_ip, 2)})
       node4:   ${element(aws_instance.demo.*.id, 3)} (${element(aws_instance.demo.*.public_ip, 3)})
       node5:   ${element(aws_instance.demo.*.id, 4)} (${element(aws_instance.demo.*.public_ip, 4)})
       node6:   ${element(aws_instance.demo.*.id, 5)} (${element(aws_instance.demo.*.public_ip, 5)})
       node7:   ${element(aws_instance.demo.*.id, 6)} (${element(aws_instance.demo.*.public_ip, 6)})
       node8:   ${element(aws_instance.demo.*.id, 7)} (${element(aws_instance.demo.*.public_ip, 7)})
       node9:   ${element(aws_instance.demo.*.id, 8)} (${element(aws_instance.demo.*.public_ip, 8)})
       node10:  ${element(aws_instance.demo.*.id, 9)} (${element(aws_instance.demo.*.public_ip, 9)})

EOF
}
