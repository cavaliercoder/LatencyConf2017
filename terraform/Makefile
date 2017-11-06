SOURCES = $(wildcard *.tf)

all: .tfplan

.tfplan: $(SOURCES)
	terraform plan -out $@

install: .tfplan
	terraform apply .tfplan
	$(MAKE) clean

clean:
	rm -f .tfplan

.PHONY: all install clean
