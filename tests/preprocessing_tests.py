import nose.tools as nt
import pandas as pd

from PyPRSVT.preprocessing import ranking, utils, svcomp15
from PyPRSVT.preprocessing.unused import regression, classification


def read_results_values_test():
    tool, df = svcomp15.svcomp_xml_to_dataframe('static/results-xml-raw/cbmc.14-12-04_1241.results.sv-comp15.mixed-examples.xml')
    nt.assert_equal(tool, 'cbmc')
    nt.assert_equal(df.iloc[0]['options'], '--32')
    nt.assert_equal(df.iloc[0]['status'], svcomp15.Status.true)
    nt.assert_equal(df.iloc[0]['cputime'], 7.627101835)
    nt.assert_equal(df.iloc[0]['walltime'], 7.66226601601)
    nt.assert_equal(df.iloc[0]['mem_usage'], 2848837632)
    nt.assert_equal(df.iloc[0]['expected_status'], svcomp15.Status.false)
    nt.assert_equal(df.iloc[0]['property_type'], svcomp15.PropertyType.unreachability)
    nt.assert_equal(df.iloc[1]['status_msg'], 'OUT OF MEMORY')
    nt.assert_equal(df.iloc[1]['mem_usage'], 15000002560)
    nt.assert_equal(df.iloc[2]['walltime'], 850.019608021)
    nt.assert_equal(df.iloc[2]['property_type'], svcomp15.PropertyType.memory_safety)
    nt.assert_equal(df.iloc[3]['property_type'], svcomp15.PropertyType.termination)
    nt.assert_equal(df.iloc[3]['options'], '--64')


def match_status_str_test():
    nt.assert_equal(svcomp15._match_status_str('true'), svcomp15.Status.true)
    nt.assert_equal(svcomp15._match_status_str('false'), svcomp15.Status.false)
    nt.assert_equal(svcomp15._match_status_str('unknown'), svcomp15.Status.unknown)
    nt.assert_equal(svcomp15._match_status_str('TIMEOUT'), svcomp15.Status.unknown)
    nt.assert_equal(svcomp15._match_status_str('OUT OF MEMORY'), svcomp15.Status.unknown)
    nt.assert_equal(svcomp15._match_status_str('false(reach)'), svcomp15.Status.false)
    nt.assert_equal(svcomp15._match_status_str('error'), svcomp15.Status.unknown)
    nt.assert_equal(svcomp15._match_status_str('EXCEPTION (Gremlins)'), svcomp15.Status.unknown)


def read_results_no_none_test():
    _, df = svcomp15.svcomp_xml_to_dataframe('static/results-xml-raw/cbmc.14-12-04_1241.results.sv-comp15.mixed-examples.xml')
    for __, series in df.iterrows():
        for ___, value in series.iteritems():
            nt.assert_not_equal(value, None)
            nt.assert_true(not pd.isnull(value))


def witnesscheck_test():
    category_results_nowc = svcomp15.read_category('static/results-xml-raw', 'mixed-examples', False)
    category_results = svcomp15.read_category('static/results-xml-raw', 'mixed-examples', True)
    nt.assert_equal(category_results_nowc['smack'].iloc[0]['status'], svcomp15.Status.false)
    nt.assert_equal(category_results['smack'].iloc[0]['status'], svcomp15.Status.unknown)
    nt.assert_equal(category_results_nowc['cbmc'].iloc[0]['status'], svcomp15.Status.true)
    nt.assert_equal(category_results['cbmc'].iloc[0]['status'], svcomp15.Status.true)

def derive_total_benchmark_order_test():
    category_results = svcomp15.read_category('static/results-xml-raw', 'mixed-examples')
    r = utils.derive_total_benchmark_order(
        category_results,
        'static/sv-benchmarks/c/mixed-examples/data_structures_set_multi_proc_false-unreach-call_ground.i',
        svcomp15.compare_results)
    nt.assert_equal(r, ['cpachecker', 'smack', 'cbmc'])
