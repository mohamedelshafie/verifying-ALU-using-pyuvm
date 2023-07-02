import logging

import pyuvm
from pyuvm import *
import cocotb
from cocotb.triggers import *
from cocotb.queue import *
#from queue import Queue
from cocotb_coverage.coverage import *
from cocotb_coverage.crv import *

class transaction(uvm_sequence_item):
    def __init__(self, name="TRANSACTION"):
        super().__init__(name)
        self.a = 0
        self.b = 0
        self.op = 0
        self.c = 0
        self.out = 0

class generator(uvm_sequence):
    async def body(self):
        for i in range(8000):
            self.trans = transaction(name="trans")  # should be outside for loop
            await self.start_item(self.trans)
            self.randomize(self.trans)  # Randomize
            sample(self.trans.a, self.trans.b, self.trans.op)  # sample
            # print("in generator " + str(self.trans.a))
            # print("in generator " + str(self.trans.b))
            # print("in generator " + str(self.trans.op))
            await self.finish_item(self.trans)

    def randomize(self, tr):
        tr.a = random.randint(0, 15)
        tr.b = random.randint(0, 15)
        tr.op = random.randint(0, 3)

class driver(uvm_driver):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.dut_driver = cocotb.top
        self.drv_event = Event()

    def build_phase(self):
        self.trans = uvm_factory().create_object_by_type(transaction, name="trans")
        ConfigDB().set(None, "*", "drv_event", self.drv_event)  # don't need it since we await timer


    async def run_phase(self):
        while True:
            self.trans = await self.seq_item_port.get_next_item()
            # self.logger.info("in driver " + str(self.trans.a))
            # self.logger.info("in driver " + str(self.trans.b))
            # self.logger.info("in driver " + str(self.trans.op))
            self.dut_driver.a.value = self.trans.a
            self.dut_driver.b.value = self.trans.b
            self.dut_driver.op.value = self.trans.op
            self.seq_item_port.item_done()
            #self.drv_event.set()  # don't need it since we await timer
            await Timer(1, "ns")

class Monitor(uvm_component):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.dut_monitor = cocotb.top
        self.mon_event = None  # don't need it since we await timer

    def build_phase(self):
        self.my_analysis_port = uvm_analysis_port("my_analysis_port", self)
        self.trans = uvm_factory().create_object_by_type(transaction, name="trans")
        self.mon_event = ConfigDB().get(self, "", "drv_event")  # don't need it since we await timer

    async def run_phase(self):
        while True:  # needs modification:
            #self.mon_event.clear()  # don't need it since we await timer
            await Timer(1, "ns")

            self.trans.a = self.dut_monitor.a.value
            self.trans.b = self.dut_monitor.b.value
            self.trans.op = self.dut_monitor.op.value

            self.trans.c = self.dut_monitor.c.value
            self.trans.out = self.dut_monitor.out.value
            # problem when sending the trans itself:
            self.my_analysis_port.write((self.trans.a, self.trans.b, self.trans.op, self.trans.out, self.trans.c))
            #self.my_analysis_port.write((self.trans))
            # self.logger.info("in monitor " + str(self.trans.a))
            # self.logger.info("in monitor " + str(self.trans.b))
            # self.logger.info("in monitor " + str(self.trans.op))
            # self.logger.info("in monitor " + str(self.trans.out))
            # self.logger.info("in monitor " + str(self.trans.c))

            #await event here between monitor and driver
            #await self.mon_event.wait()  # don't need it since we await timer


class scoreboard(uvm_component):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.passed = 0  # counting number of passed tests
        self.failed = 0  # counting number of failed tests
        self.bugs_count = 0  # count number of unique bugs in the dut
        self.bugs = []  # list to append all errors happened
        self.bugs_final = []  # list to put the unique bugs in it

    def build_phase(self):
        self.trans = uvm_factory().create_object_by_type(transaction, name="trans")
        self.trans_fifo = uvm_tlm_analysis_fifo("trans_fifo", self)
        self.trans_export = self.trans_fifo.analysis_export
        self.trans_get_port = uvm_get_port("trans_get_port", self)

    def connect_phase(self):
        self.trans_get_port.connect(self.trans_fifo.get_export)

    def check_phase(self):
        #self.trans_fifo.get()  # need to try this
        while self.trans_get_port.can_get():
            _, recv = self.trans_get_port.try_get()
            #self.trans = recv
            (a, b, op, out, c) = recv

            # self.logger.info("trans= " + str(self.trans.a))
            # self.logger.info("trans= " + str(self.trans.b))
            # self.logger.info("trans= " + str(self.trans.op))
            # self.logger.info("trans= " + str(self.trans.out))
            # self.logger.info("trans= " + str(self.trans.c))

            # self.logger.info("a= " + str(a))
            # self.logger.info("b= " + str(b))
            # self.logger.info("op= " + str(op))
            # self.logger.info("out= " + str(out))
            # self.logger.info("c= " + str(c))

            if (int(op)) == 0:
                if int(a) + int(b) == int((c << 4) + out):
                    self.passed = self.passed + 1
                else:
                    self.failed = self.failed + 1
                    self.bugs.append(str(a) + str(b) + str(op))

            elif (int(op)) == 1:
                if int(a) ^ int(b) == int((c << 4) + out):
                    self.passed = self.passed + 1
                else:
                    self.failed = self.failed + 1
                    self.bugs.append(str(a) + str(b) + str(op))

            elif (int(op)) == 2:
                if int(a) & int(b) == int((c << 4) + out):
                    self.passed = self.passed + 1
                else:
                    self.failed = self.failed + 1
                    self.bugs.append(str(a) + str(b) + str(op))

            elif (int(op)) == 3:
                if int(a) | int(b) == int((c << 4) + out):
                    self.passed = self.passed + 1
                else:
                    self.failed = self.failed + 1
                    self.bugs.append(str(a) + str(b) + str(op))


            # if (int(self.trans.op)) == 0:
            #     if int(self.trans.a) + int(self.trans.b) == int((self.trans.c << 4) + self.trans.out):
            #         self.passed = self.passed + 1
            #     else:
            #         self.failed = self.failed + 1
            #         self.bugs.append(str(self.trans.a) + str(self.trans.b) + str(self.trans.op))
            #
            # elif (int(self.trans.op)) == 1:
            #     if int(self.trans.a) ^ int(self.trans.b) == int((self.trans.c << 4) + self.trans.out):
            #         self.passed = self.passed + 1
            #     else:
            #         self.failed = self.failed + 1
            #         self.bugs.append(str(self.trans.a) + str(self.trans.b) + str(self.trans.op))
            #
            # elif (int(self.trans.op)) == 2:
            #     if int(self.trans.a) & int(self.trans.b) == int((self.trans.c << 4) + self.trans.out):
            #         self.passed = self.passed + 1
            #     else:
            #         self.failed = self.failed + 1
            #         self.bugs.append(str(self.trans.a) + str(self.trans.b) + str(self.trans.op))
            #
            # elif (int(self.trans.op)) == 3:
            #     if int(self.trans.a) | int(self.trans.b) == int((self.trans.c << 4) + self.trans.out):
            #         self.passed = self.passed + 1
            #     else:
            #         self.failed = self.failed + 1
            #         self.bugs.append(str(self.trans.a) + str(self.trans.b) + str(self.trans.op))

            self.bugs_final = list(dict.fromkeys(self.bugs))  # removing duplicates to get the unique bugs
            self.bugs_count = len(self.bugs_final)  # counting the unique bugs

    def final_phase(self):
        self.logger.info("passed = " + str(self.passed))
        self.logger.info("failed = " + str(self.failed))
        self.logger.info("unique bugs = " + str(self.bugs_count))


class environment(uvm_env):
    def __init__(self, name="ENVironment", parent=None):
        super().__init__(name=name, parent=parent)

    def build_phase(self):
        self.seqr = uvm_sequencer("seqr", self)
        ConfigDB().set(None, "*", "seqr", self.seqr)

        self.driver = driver("drv1", self)
        self.monitor = Monitor("mon1", self)
        self.scoreboard = scoreboard("sco1", self)

    def connect_phase(self):
        self.driver.seq_item_port.connect(self.seqr.seq_item_export)
        self.monitor.my_analysis_port.connect(self.scoreboard.trans_export)


# coverage calculations:
Coverage = coverage_section(
    CoverPoint("top.a", vname="a", bins=list(range(0, 16))),
    CoverPoint("top.b", vname="b", bins=list(range(0, 16))),
    CoverPoint("top.op", vname="op", bins=list(range(0, 4))),
    CoverCross("top.all_cases", items=["top.a", "top.b", "top.op"])
)


@Coverage
def sample(a, b, op):
    pass


@pyuvm.test()
class test1(uvm_test):
    def build_phase(self):
        self.environment = environment("env1", self)

    def end_of_elaboration_phase(self):
        self.seqr = ConfigDB().get(self, "", "seqr")

    async def run_phase(self):
        self.raise_objection()
        self.generator = generator("gen1")  # why create in run phase
        await self.generator.start(self.seqr)
        await Timer(2, "ns")  # check this (waiting for last transaction to reach monitor and put in analysis port)
        self.drop_objection()

    def final_phase(self):
        # Print coverage:
        coverage_db.export_to_xml(filename="coverage.xml")

        # Print factory:
        uvm_factory().print(2)
