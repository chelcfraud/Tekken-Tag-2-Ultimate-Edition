#pragma once
#include "imported_hitboxes.h"

namespace cafe::title::hitboxes {
// T8 8375: slot:X, Y:Z, half-height:radius; 8376 disables the slot.
constexpr uint32_t kHurtX=0x8f10, kHurtYZ=0x8f11, kHurtSize=0x8f12, kHurtClear=0x8f13;
inline int packed_high(uint32_t v) {
    const int n=static_cast<int16_t>(v>>16);
    return n+(n<0); // source property's signed packed-coordinate convention
}
struct AuxiliaryHurtbox {
    uint32_t move=0;
    Vec offset{};
    float half_height=0,radius=0;
    bool enabled=false;
    void property(uint32_t owner,uint32_t id,uint32_t value) {
        if(move!=owner) {*this={};move=owner;}
        if(id==kHurtClear)enabled=false;
        if(id==kHurtX) {offset[0]=static_cast<int16_t>(value);enabled=false;}
        if(id==kHurtYZ)offset={offset[0],float(packed_high(value)),float(static_cast<int16_t>(value))};
        if(id==kHurtSize) {
            half_height=float(packed_high(value));radius=float(static_cast<int16_t>(value));
            enabled=half_height>=0 && radius>0;
        }
    }
    bool active(uint32_t owner) const {return enabled && move==owner;}
    std::array<float,6> capsule(const Frame& trans) const {
        const auto p=transform(trans,offset);
        return {p[0],p[1],p[2],half_height,radius*radius,2*radius};
    }
};
}
