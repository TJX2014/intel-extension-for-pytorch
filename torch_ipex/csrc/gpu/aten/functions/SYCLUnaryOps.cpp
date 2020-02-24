#include <ATen/ATen.h>
#include <ATen/LegacyTHFunctionsSYCL.h>

namespace at { namespace native {

Tensor& _clamp_out_sycl(
    Tensor& result,
    const Tensor& self,
    optional<Scalar> min,
    optional<Scalar> max) {
  if (min && max) {
    legacy::sycl::_th_clamp_out(result, self, *min, *max);
  } else if (max) {
    legacy::sycl::_th_clamp_max_out(result, self, *max);
  } else if (min) {
    legacy::sycl::_th_clamp_min_out(result, self, *min);
  } else {
    AT_ERROR("At least one of 'min' or 'max' must not be None");
  }
  return result;
}

Tensor& _clamp__sycl(Tensor& self, optional<Scalar> min, optional<Scalar> max) {
  return _clamp_out_sycl(self, self, min, max);
}

Tensor& _clamp_max__sycl(Tensor& self, Scalar max) {
    return legacy::sycl::_th_clamp_max_out(self, self, max);
}

Tensor& _clamp_max_out_sycl(Tensor& result, const Tensor& self, Scalar max) {
    return legacy::sycl::_th_clamp_max_out(result, self, max);
}



Tensor& _clamp_min__sycl(Tensor& self, Scalar min) {
  return legacy::sycl::_th_clamp_min_out(self, self, min);
}

Tensor& _clamp_min_out_sycl(Tensor& result, const Tensor& self, Scalar min) {
  return legacy::sycl::_th_clamp_min_out(result, self, min);
}

#define IMPLEMENT_UNARY_OP_PREQUEL(op)                           \
  Tensor& _##op##__sycl(Tensor& self) {                          \
    return legacy::sycl::_th_##op##_out(self, self);             \
  }                                                              \
  Tensor& _##op##_out_sycl(Tensor& result, const Tensor& self) { \
    return legacy::sycl::_th_##op##_out(result, self);           \
  }

IMPLEMENT_UNARY_OP_PREQUEL(abs)
IMPLEMENT_UNARY_OP_PREQUEL(acos)
IMPLEMENT_UNARY_OP_PREQUEL(asin)
IMPLEMENT_UNARY_OP_PREQUEL(atan)
IMPLEMENT_UNARY_OP_PREQUEL(ceil)
IMPLEMENT_UNARY_OP_PREQUEL(cos)
IMPLEMENT_UNARY_OP_PREQUEL(cosh)
IMPLEMENT_UNARY_OP_PREQUEL(erf)
IMPLEMENT_UNARY_OP_PREQUEL(erfc)
IMPLEMENT_UNARY_OP_PREQUEL(exp)
IMPLEMENT_UNARY_OP_PREQUEL(expm1)
IMPLEMENT_UNARY_OP_PREQUEL(floor)
IMPLEMENT_UNARY_OP_PREQUEL(log)
IMPLEMENT_UNARY_OP_PREQUEL(log10)
IMPLEMENT_UNARY_OP_PREQUEL(log1p)
IMPLEMENT_UNARY_OP_PREQUEL(log2)
IMPLEMENT_UNARY_OP_PREQUEL(round)
IMPLEMENT_UNARY_OP_PREQUEL(rsqrt)
IMPLEMENT_UNARY_OP_PREQUEL(sin)
IMPLEMENT_UNARY_OP_PREQUEL(sinh)
IMPLEMENT_UNARY_OP_PREQUEL(sqrt)
IMPLEMENT_UNARY_OP_PREQUEL(tan)
IMPLEMENT_UNARY_OP_PREQUEL(tanh)
IMPLEMENT_UNARY_OP_PREQUEL(trunc)

}}
