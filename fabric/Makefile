LAYOUT := dot

SOURCES = $(wildcard *.dot)
PNGS = $(patsubst %.dot, %.png, $(SOURCES))
SVGS = $(patsubst %.dot, %.svg, $(SOURCES))

all: $(PNGS) $(SVGS)

%.png: %.dot
	$(LAYOUT) -Tpng $< -o$@

%.svg: %.dot
	$(LAYOUT) -Tsvg $< -o$@

clean:
	rm -vf $(PNGS) $(SVGS)
