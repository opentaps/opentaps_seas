import opentaps_seas.core.pysam_utils as pysam_utils


def run():
    result = pysam_utils.run_calculation("demo-site-1-sample_meter", 2019, 7)
    print(result)
