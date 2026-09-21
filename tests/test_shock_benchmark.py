import pytest

from mesm.models.changepoint import page_hinkley_flags
from mesm.evaluation.shock_benchmark import robust_standardize


def test_page_hinkley_detects_persistent_shift():
    values=[0.0]*12+[3.0]*8
    flags=page_hinkley_flags(values,threshold=4.0,delta=0.05,warmup=12)
    assert any(flags[12:])


def test_robust_standardize_centers_median():
    z=robust_standardize([-2.0,-1.0,0.0,1.0,20.0])
    assert z[2] == pytest.approx(0.0)
