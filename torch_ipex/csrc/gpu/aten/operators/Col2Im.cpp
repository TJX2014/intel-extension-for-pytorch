#include <ATen/ATen.h>
#include <ATen/native/TensorIterator.h>
#include <ATen/div_rtn.h>

#include <core/ApplyUtils.h>
#include <core/DPCPP.h>
#include <core/TensorImplUtils.h>
#include <core/DPCPPUtils.h>
#include <core/Memory.h>
#include <ATen/aten_ipex_type_dpcpp.h>

#include <mkldnn.hpp>

#include "Im2Col.h"
#include "Im2ColShapeCheck.h"

using namespace mkldnn;
using namespace at::dpcpp;
using namespace at::native;

namespace at {
namespace AtenIpexTypeDPCPP {
namespace impl {

static void col2im_out_template(
    Tensor& output,
    const Tensor& input_,
    IntArrayRef output_size,
    IntArrayRef kernel_size,
    IntArrayRef dilation,
    IntArrayRef padding,
    IntArrayRef stride) {
  TORCH_CHECK(
      output_size.size() == 2,
      "It is expected output_size equals to 2, but got size ",
      output_size.size());

  TORCH_CHECK(
      kernel_size.size() == 2,
      "It is expected kernel_size equals to 2, but got size ",
      kernel_size.size());

  TORCH_CHECK(
      dilation.size() == 2,
      "It is expected dilation equals to 2, but got size ",
      dilation.size());

  TORCH_CHECK(
      padding.size() == 2,
      "It is expected padding equals to 2, but got size ",
      padding.size());

  TORCH_CHECK(
      stride.size() == 2,
      "It is expected stride equals to 2, but got size ",
      stride.size());

  int64_t output_height = output_size[0];
  int64_t output_width = output_size[1];
  int64_t kernel_height = kernel_size[0];
  int64_t kernel_width = kernel_size[1];
  int64_t dilation_height = dilation[0];
  int64_t dilation_width = dilation[1];
  int64_t pad_height = padding[0];
  int64_t pad_width = padding[1];
  int64_t stride_height = stride[0];
  int64_t stride_width = stride[1];

  col2im_shape_check(
      input_,
      Tensor(),
      output_height,
      output_width,
      kernel_height,
      kernel_width,
      dilation_height,
      dilation_width,
      pad_height,
      pad_width,
      stride_height,
      stride_width);

  Tensor input = input_.contiguous();

  bool batched_input = true;
  if (input.dim() == 2) {
    // Force batch
    batched_input = false;
    input.resize_({1, input.size(0), input.size(1)});
  }

  int64_t batch_size = input.size(0);
  int64_t n_input_plane = input.size(1);
  int64_t n_output_plane = n_input_plane / (kernel_width * kernel_height);

  output.resize_({batch_size, n_output_plane, output_height, output_width});
  output.zero_();

  AT_DISPATCH_FLOATING_TYPES_AND_HALF(
      input.scalar_type(), "col2im_out_dpcpp", [&] {
        Tensor input_n = Tensor();
        Tensor output_n = Tensor();

        int64_t height_col = (output_height + 2 * pad_height -
                              (dilation_height * (kernel_height - 1) + 1)) /
                stride_height +
            1;
        int64_t width_col = (output_width + 2 * pad_width -
                             (dilation_width * (kernel_width - 1) + 1)) /
                stride_width +
            1;

        for (int64_t elt = 0; elt < batch_size; elt++) {
          input_n = input.select(0, elt);
          output_n = output.select(0, elt);

          ::col2im_kernel<scalar_t>(
              input_n.data_ptr<scalar_t>(),
              n_output_plane,
              output_height,
              output_width,
              height_col,
              width_col,
              kernel_height,
              kernel_width,
              pad_height,
              pad_width,
              stride_height,
              stride_width,
              dilation_height,
              dilation_width,
              output_n.data_ptr<scalar_t>());
        }

        if (!batched_input) {
          output.resize_({n_output_plane, output_height, output_width});
        }
      });
}


void col2im_backward_out_template(
    Tensor& grad_input,
    const Tensor& grad_output,
    IntArrayRef kernel_size,
    IntArrayRef dilation,
    IntArrayRef padding,
    IntArrayRef stride) {
  // im2col_out_cpu checks size of kernel_size, dilation, padding and stride
  at::AtenIpexTypeDPCPP::im2col_out(
      grad_input, grad_output, kernel_size, dilation, padding, stride);
}

} // namespace impl

Tensor& col2im_out(
    Tensor& out,
    const Tensor& self,
    IntArrayRef output_size,
    IntArrayRef kernel_size,
    IntArrayRef dilation,
    IntArrayRef padding,
    IntArrayRef stride) {
  impl::col2im_out_template(
      out, self, output_size, kernel_size, dilation, padding, stride);
  return out;
}

Tensor col2im(
    const Tensor& self,
    IntArrayRef output_size,
    IntArrayRef kernel_size,
    IntArrayRef dilation,
    IntArrayRef padding,
    IntArrayRef stride) {
  Tensor output = at::empty_like(self);

  impl::col2im_out_template(
      output, self, output_size, kernel_size, dilation, padding, stride);
  return output;
}

Tensor& col2im_backward_out(
    Tensor& grad_input,
    const Tensor& grad_output,
    IntArrayRef kernel_size,
    IntArrayRef dilation,
    IntArrayRef padding,
    IntArrayRef stride) {
  impl::col2im_backward_out_template(
      grad_input, grad_output, kernel_size, dilation, padding, stride);
  return grad_input;
}

Tensor col2im_backward(
    const Tensor& grad_output,
    IntArrayRef kernel_size,
    IntArrayRef dilation,
    IntArrayRef padding,
    IntArrayRef stride) {
  Tensor grad_input = at::empty_like(grad_output);

  impl::col2im_backward_out_template(
      grad_input, grad_output, kernel_size, dilation, padding, stride);
  return grad_input;
}

} // namespace AtenIpexTypeDPCPP
} // namespace at
