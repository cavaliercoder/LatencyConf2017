LAYOUT := dot

GRAPH_SOURCES = $(wildcard *.dot)
SVGS = $(patsubst %.dot, %.svg, $(GRAPH_SOURCES))

all: $(SVGS)

%.svg: %.dot
	$(LAYOUT) -Tsvg $< -o$@

clean:
	rm -vf $(SVGS)

run: $(SVGS)
	present -notes

.PHONY: all clean run
