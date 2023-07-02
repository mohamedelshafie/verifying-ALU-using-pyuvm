TOPLEVEL_LANG ?= verilog
SIM ?= questa #questa #icarus
PWD=$(shell pwd)


ifeq ($(TOPLEVEL_LANG),verilog)
    VERILOG_SOURCES = $(PWD)/DUT.sv
else ifeq ($(TOPLEVEL_LANG),vhdl)
    VHDL_SOURCES = $(PWD)/DUT.vhdl
else
    $(error A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG))
endif

TOPLEVEL := ALU
MODULE   := pyuvm_alu

include $(shell cocotb-config --makefiles)/Makefile.sim