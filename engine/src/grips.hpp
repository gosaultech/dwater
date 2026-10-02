// damned_waters/engine/src/grips.hpp
// Purpose: how the survivor holds his guns: each grip fitted by `damned_waters --fitgrips`
// (grip_fit.cpp) and written to grips_fitted.inc, which this wraps in a namespace.
#ifndef DW_GRIPS_HPP
#define DW_GRIPS_HPP
#include "dw/character.hpp"

namespace dw::grips {
#include "grips_fitted.inc"
}  // namespace dw::grips

#endif
