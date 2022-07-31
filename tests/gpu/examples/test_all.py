import torch
from torch.testing._internal.common_utils import TestCase

import intel_extension_for_pytorch

cpu_device = torch.device("cpu")
dpcpp_device = torch.device("xpu")


class TestTorchMethod(TestCase):
    def test_all(self, dtype=torch.float):
        x_cpu = torch.randn([1, 3, 8, 2], device=cpu_device).byte() % 2
        x_dpcpp = x_cpu.to(dpcpp_device)

        y_cpu = x_cpu.all()
        y_dpcpp = x_dpcpp.all()

        self.assertEqual(y_cpu, y_dpcpp.to("cpu"))

        x_cpu = torch.randn([1], device=cpu_device).byte() % 2
        x_dpcpp = x_cpu.to(dpcpp_device)

        y_cpu = x_cpu.all()
        y_dpcpp = x_dpcpp.all()

        self.assertEqual(y_cpu, y_dpcpp.to("cpu"))

        x_cpu = torch.Tensor()
        x_dpcpp = x_cpu.to(dpcpp_device)

        y_cpu = x_cpu.all()
        y_dpcpp = x_dpcpp.all()

        self.assertEqual(y_cpu, y_dpcpp.to("cpu"))

        x_cpu = torch.randn([461, 42, 2, 5], device=cpu_device).byte() % 2
        x_dpcpp = x_cpu.to(dpcpp_device)

        y_cpu = x_cpu.all()
        y_dpcpp = x_dpcpp.all()

        self.assertEqual(y_cpu, y_dpcpp.to("cpu"))

        x_cpu = torch.randn([3, 2, 5, 2], device=cpu_device).byte() % 2
        x_dpcpp = x_cpu.to(dpcpp_device)

        y_cpu = x_cpu.all(3)
        y_dpcpp = x_dpcpp.all(3)

        self.assertEqual(True, y_cpu.eq(y_dpcpp.to("cpu")).all())

        x_cpu = torch.randn([359, 50, 7], device=cpu_device).byte() % 2
        x_dpcpp = x_cpu.to(dpcpp_device)

        y_cpu = x_cpu.all(2, True)
        y_dpcpp = x_dpcpp.all(2, True)

        self.assertEqual(True, y_cpu.eq(y_dpcpp.to("cpu")).all())
