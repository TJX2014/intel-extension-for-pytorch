import unittest
import intel_extension_for_pytorch as ipex
from common_utils import TestCase
import time, sys
from intel_extension_for_pytorch.cpu.launch import *
import os
import glob
import subprocess 

class TestLauncher(TestCase):
    def del_env(self, env_name):

        if env_name in os.environ:
            del os.environ[env_name]

    def find_lib(self, lib_type):
        library_paths = []
        if "CONDA_PREFIX" in os.environ:
            library_paths.append(os.environ["CONDA_PREFIX"] + "/lib/")
        elif "VIRTUAL_ENV" in os.environ:
            library_paths.append(os.environ["VIRTUAL_ENV"] + "/lib/")

        library_paths += ["{}/.local/lib/".format(expanduser("~")), "/usr/local/lib/",
                         "/usr/local/lib64/", "/usr/lib/", "/usr/lib64/"]
        lib_find = False
        for lib_path in library_paths:
            library_file = lib_path + "lib" + lib_type + ".so"
            matches = glob.glob(library_file)
            if len(matches) > 0:
                lib_find = True
                break
        return lib_find

    def test_iomp_memory_allocator_setup(self):
       launcher = Launcher()
       self.del_env("OMP_NUM_THREADS")
       self.del_env("LD_PRELOAD")
       self.del_env("KMP_AFFINITY")
       self.del_env("KMP_BLOCKTIME")
       launcher.set_multi_thread_and_allocator(10, disable_iomp=False, enable_tcmalloc=True)
       find_iomp5 = self.find_lib("iomp5")
       find_tcmalloc = self.find_lib("tcmalloc")
       ld_preload_in_os = "LD_PRELOAD" in os.environ
       iomp5_enabled = "libiomp5.so" in os.environ["LD_PRELOAD"] if ld_preload_in_os else False
       tcmalloc_enabled = "libtcmalloc.so" in os.environ["LD_PRELOAD"] if ld_preload_in_os else False
       self.assertEqual(find_iomp5, iomp5_enabled)
       self.assertEqual(find_tcmalloc, tcmalloc_enabled)
       launcher.set_multi_thread_and_allocator(10, disable_iomp=False, enable_tcmalloc=False, enable_jemalloc=True)
       find_jemalloc = self.find_lib("jemalloc")
       jemalloc_enabled = "libjemalloc.so" in os.environ["LD_PRELOAD"] if ld_preload_in_os else False
       self.assertEqual(find_jemalloc, jemalloc_enabled)
       kmp_affinity_enabled = "KMP_AFFINITY" in os.environ and os.environ["KMP_AFFINITY"] == "granularity=fine,compact,1,0"
       block_time_enabled = "KMP_BLOCKTIME" in os.environ and os.environ["KMP_BLOCKTIME"] == "1"
       self.assertEqual(kmp_affinity_enabled, True)
       self.assertEqual(block_time_enabled, True)
       if jemalloc_enabled:
           self.assertEqual(jemalloc_enabled, "MALLOC_CONF" in os.environ)

    def test_mpi_pin_domain_and_ccl_worker_affinity(self):
       launcher = DistributedTrainingLauncher()
       total_cores = 56
       proc_per_node = 2
       ccl_worker_count = 4
       pin_doamin = launcher.get_mpi_pin_domain(proc_per_node, ccl_worker_count, total_cores)
       expect_pin_domain = "[0xffffff0,0xffffff00000000,]"
       self.assertEqual(pin_doamin, expect_pin_domain)
       ccl_worker_affinity = launcher.get_ccl_worker_affinity(proc_per_node, ccl_worker_count, total_cores)
       expected_ccl_worker_affinity = "0,1,2,3,28,29,30,31"
       self.assertEqual(ccl_worker_affinity, expected_ccl_worker_affinity)
    
    def test_numactl_core_affinity(self):
        cpuinfo = CPUinfo()
        num_physical_cores = cpuinfo.physical_core_nums()
        
        launcher = MultiInstanceLauncher()
        numactl_available = launcher.is_numactl_available()
        
        if numactl_available:
            expected_core_affinity = "numactl -C {}-{}".format(str(0), str(num_physical_cores-1))
            cmd = ["python", "-m", "intel_extension_for_pytorch.cpu.launch", "--no_python", "hostname"]
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            assert r.returncode == 0
            assert expected_core_affinity in str(r.stdout, "utf-8")
    
    def test_taskset_core_affinity(self):
        cpuinfo = CPUinfo()
        num_physical_cores = cpuinfo.physical_core_nums()
    
        expected_core_affinity = "taskset -c {}-{}".format(str(0), str(num_physical_cores-1))
        cmd = ["python", "-m", "intel_extension_for_pytorch.cpu.launch", "--disable_numactl", "--no_python", "hostname"]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert r.returncode == 0
        assert expected_core_affinity in str(r.stdout, "utf-8")

    def test_core_affinity_with_skip_cross_node_cores(self):
        cpuinfo = CPUinfo()
        num_nodes = cpuinfo.node_nums()
        num_cores_per_node = len(cpuinfo.node_physical_cores[0])
        
        if num_nodes > 1:
            # ncore_per_instance that guarantees cross-node cores binding without --skip_cross_node_cores
            ncore_per_instance = num_cores_per_node -1
            
            cmd = "python -m intel_extension_for_pytorch.cpu.launch --ncore_per_instance {} --skip_cross_node_cores --no_python hostname".format(ncore_per_instance)
            r = subprocess.run(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            assert r.returncode == 0
            
            for i in range(num_nodes):
                node_i_start_core = i*num_cores_per_node
                expected_node_i_core_affinity = "-c {}-{}".format(str(node_i_start_core), str(node_i_start_core + ncore_per_instance -1))
                assert expected_node_i_core_affinity in str(r.stdout, "utf-8").lower()
    
    def test_core_affinity_with_skip_cross_node_cores_and_use_logical_core(self):
        cpuinfo = CPUinfo()
        num_nodes = cpuinfo.node_nums()
        num_cores_per_node = len(cpuinfo.node_physical_cores[0])
        num_threads_per_core = int(cpuinfo.logical_core_nums()/cpuinfo.physical_core_nums())

        if num_nodes > 1 and num_threads_per_core > 1:
            # ncore_per_instance that guarantees cross-node cores binding without --skip_cross_node_cores
            ncore_per_instance = num_cores_per_node -1
            
            cmd = "python -m intel_extension_for_pytorch.cpu.launch --ncore_per_instance {} --use_logical_core --skip_cross_node_cores --no_python hostname".format(ncore_per_instance)
            r = subprocess.run(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            assert r.returncode == 0
            
            for i in range(num_nodes):
                node_i_physical_start_core = i*num_cores_per_node
                node_i_logical_start_core = (i+num_nodes)*num_cores_per_node
                expected_node_i_physical_core_affinity = "-c {}-{}".format(str(node_i_physical_start_core), str(node_i_physical_start_core + ncore_per_instance -1))
                expected_node_i_logical_core_affinity = "-c {}-{}".format(str(node_i_logical_start_core), str(node_i_logical_start_core + ncore_per_instance -1))
                assert expected_node_i_physical_core_affinity in str(r.stdout, "utf-8").lower()
                assert expected_node_i_logical_core_affinity in str(r.stdout, "utf-8").lower()
    
    def test_core_affinity_with_skip_cross_node_cores_and_node_id_use_logical_core(self):
        cpuinfo = CPUinfo()
        num_nodes = cpuinfo.node_nums()
        num_cores_per_node = len(cpuinfo.node_physical_cores[0])
        num_threads_per_core = int(cpuinfo.logical_core_nums()/cpuinfo.physical_core_nums())
        
        if num_nodes > 1 and num_threads_per_core > 1:
            # ncore_per_instance that guarantees cross-node cores binding without --skip_cross_node_cores
            ncore_per_instance = num_cores_per_node -1
            
            cmd = "python -m intel_extension_for_pytorch.cpu.launch --ncore_per_instance {} --node_id 0 --use_logical_core --skip_cross_node_cores --no_python hostname".format(ncore_per_instance)
            r = subprocess.run(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            assert r.returncode == 0
            
            node_0_physical_start_core = 0*num_cores_per_node 
            node_0_logical_start_core = (0+num_nodes)*num_cores_per_node
            
            expected_node_0_physical_core_affinity = "-c {}-{}".format(str(node_0_physical_start_core), str(node_0_physical_start_core + ncore_per_instance -1))
            expected_node_0_logical_core_affinity = "-c {}-{}".format(str(node_0_logical_start_core), str(node_0_logical_start_core + ncore_per_instance -1))
            
            assert expected_node_0_physical_core_affinity in str(r.stdout, "utf-8").lower()
            assert expected_node_0_logical_core_affinity in str(r.stdout, "utf-8").lower()
    
    def test_skip_cross_node_cores_with_too_many_ncore_per_instance(self):
        cpuinfo = CPUinfo()
        num_nodes = cpuinfo.node_nums()
        num_cores_per_node = len(cpuinfo.node_physical_cores[0])
        
        if num_nodes > 1:
            # ncore_per_instance that is too many to skip cross-node cores 
            ncore_per_instance = num_cores_per_node +1
            
            expected_msg = "Please make sure --ncore_per_instance < core(s) per socket"
            
            cmd = "python -m intel_extension_for_pytorch.cpu.launch --ncore_per_instance {} --skip_cross_node_cores --no_python hostname".format(ncore_per_instance)
            r = subprocess.run(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            assert r.returncode != 0
            assert expected_msg in str(r.stdout, "utf-8")
    
    def test_skip_cross_node_cores_with_divisible_ncore_per_instance(self):
        cpuinfo = CPUinfo()
        num_nodes = cpuinfo.node_nums()
        num_cores_per_node = len(cpuinfo.node_physical_cores[0])
        
        if num_nodes > 1:
            # ncore_per_instance that guarantees no cross-node cores binding 
            ncore_per_instance = num_cores_per_node
            
            expected_msg = "--skip_cross_node_cores is set, but there are no cross-node cores"
            
            cmd = "python -m intel_extension_for_pytorch.cpu.launch --ncore_per_instance {} --skip_cross_node_cores --no_python hostname".format(ncore_per_instance)
            r = subprocess.run(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            assert r.returncode == 0
            assert expected_msg in str(r.stdout, "utf-8")

if __name__ == '__main__':
    test = unittest.main()
