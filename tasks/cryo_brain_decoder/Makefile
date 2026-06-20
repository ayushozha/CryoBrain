SHELL := /bin/bash

VERILATOR ?= verilator
YOSYS ?= yosys
PYTHON ?= python3

RTL := rtl/cryo_brain_decoder.sv
VISIBLE_TB := dv/visible_tb.sv
BUILD_DIR := build
REPORT_DIR := reports

.PHONY: test synth lint clean

test:
	mkdir -p $(BUILD_DIR)
	$(VERILATOR) --binary --timing -Wno-fatal --top-module cryo_brain_decoder_visible_tb \
		-Mdir $(BUILD_DIR)/obj_visible -o cryo_brain_decoder_visible \
		$(RTL) $(VISIBLE_TB)
	$(BUILD_DIR)/obj_visible/cryo_brain_decoder_visible

synth:
	mkdir -p $(REPORT_DIR)
	$(YOSYS) -q -s synth/synth.ys

lint:
	$(VERILATOR) --lint-only -Wall -Wno-fatal --top-module cryo_brain_decoder $(RTL)

clean:
	rm -rf $(BUILD_DIR) $(REPORT_DIR)