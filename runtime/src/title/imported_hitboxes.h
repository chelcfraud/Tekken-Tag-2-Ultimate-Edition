#pragma once
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <map>
#include <optional>
#include <span>
#include <stdexcept>
#include <vector>

namespace cafe::title::hitboxes {
using Vec = std::array<float,3>;
struct Frame { Vec origin{}; std::array<Vec,3> axes{}; };
struct Endpoint {
    uint32_t kind=0, a=0, b=0, bone_a=0, bone_b=0;
    Vec offset_a{},offset_b{};
};
struct Shape {
    uint32_t first=0,last=0;
    float radius=0,height=0;
    Endpoint a,b;
    bool active(uint32_t frame) const { return first<=frame && frame<=last; }
};
using Moves = std::map<uint32_t,std::vector<Shape>>;
struct Segment { Vec a{},b{}; };

inline Vec transform(const Frame& f, const Vec& p) {
    Vec out=f.origin;
    for (int c=0;c<3;++c)
        for (int k=0;k<3;++k) out[c]+=p[k]*f.axes[k][c];
    return out;
}
inline Frame compose(const Frame& local, const Frame& parent) {
    Frame out;
    out.origin=transform(parent,local.origin);
    for(int r=0;r<3;++r)
        for(int c=0;c<3;++c)
            for(int k=0;k<3;++k)out.axes[r][c]+=local.axes[r][k]*parent.axes[k][c];
    return out;
}
inline bool finite(const Vec& p) {
    return std::isfinite(p[0]) && std::isfinite(p[1]) && std::isfinite(p[2]);
}

template<class Point,class Bone,class Weapon>
std::optional<Vec> position(const Endpoint& e, Point point, Bone bone, Weapon weapon, float floor) {
    auto offset_point=[&](uint32_t p,uint32_t b,const Vec& offset)->std::optional<Vec> {
        auto origin=point(p); auto f=bone(b);
        if (!origin || !f) return std::nullopt;
        f->origin=*origin;
        return transform(*f,offset);
    };
    std::optional<Vec> out;
    switch(e.kind) {
    case 0: out=point(e.a); break;
    case 1: out=offset_point(e.a,e.bone_a,e.offset_a); break;
    case 2: if(auto f=weapon(e.a)) out=transform(*f,e.offset_a); break;
    case 3: {
        auto a=offset_point(e.a,e.bone_a,e.offset_a), b=offset_point(e.b,e.bone_b,e.offset_b);
        if(a && b) { Vec p{}; for(int i=0;i<3;++i)p[i]=((*a)[i]+(*b)[i])*0.5f; out=p; }
        break;
    }
    case 4: if(auto f=bone(e.bone_a)) {
        f->origin[1]=floor;
        // Source Trans axes are unit axes; the native root carries model scale.
        for(auto& axis:f->axes) {
            const float length=std::hypot(axis[0],axis[1],axis[2]);
            if(!(length>0.00001f)) return std::nullopt;
            for(float& v:axis)v/=length;
        }
        out=transform(*f,e.offset_a);
        break;
    }
    default: break;
    }
    return out && finite(*out) ? out : std::nullopt;
}

inline Segment segment(Vec a, Vec b, const Vec& previous, float height, bool swept) {
    if(height>0) { b=a; a[1]+=height*0.5f; b[1]-=height*0.5f; }
    else if(swept) b=previous;
    return {a,b};
}

inline Moves read(std::span<const uint8_t> data, uint32_t moveset_crc) {
    size_t at=0;
    auto u32=[&]() {
        if(at+4>data.size())throw std::runtime_error("truncated imported hitboxes");
        const uint32_t v=uint32_t(data[at]) | uint32_t(data[at+1])<<8 |
            uint32_t(data[at+2])<<16 | uint32_t(data[at+3])<<24;
        at+=4; return v;
    };
    auto number=[&]() {
        const float v=std::bit_cast<float>(u32());
        if(!std::isfinite(v) || std::abs(v)>1000000)throw std::runtime_error("invalid hitbox coordinate");
        return v;
    };
    if(u32()!=0x42483854 || u32()!=1 || u32()!=moveset_crc)
        throw std::runtime_error("imported hitboxes do not match this moveset/version");
    const uint32_t count=u32();
    if(count>65536)throw std::runtime_error("too many imported hitbox moves");
    auto endpoint=[&]() {
        Endpoint e; e.kind=u32();e.a=u32();e.b=u32();e.bone_a=u32();e.bone_b=u32();
        for(float& v:e.offset_a)v=number();
        for(float& v:e.offset_b)v=number();
        if(e.kind>5 || e.bone_a>=4096 || e.bone_b>=4096 ||
            (e.kind==2 ? e.a>=20 : e.kind<4 && (e.a>77 || e.b>77)))
            throw std::runtime_error("invalid imported hitbox endpoint");
        return e;
    };
    Moves moves;
    for(uint32_t i=0;i<count;++i) {
        const uint32_t key=u32(),n=u32();
        if(!n || n>8 || moves.contains(key))throw std::runtime_error("invalid imported hitbox move");
        auto& shapes=moves[key];
        for(uint32_t j=0;j<n;++j) {
            Shape s;s.first=u32();s.last=u32();s.radius=number();s.height=number();s.a=endpoint();s.b=endpoint();
            if(s.first>s.last || s.last>100000 || s.radius<0 || s.height<0 || s.a.kind==5)
                throw std::runtime_error("invalid imported hitbox shape");
            shapes.push_back(s);
        }
    }
    if(at!=data.size())throw std::runtime_error("trailing imported hitbox data");
    return moves;
}
} // namespace cafe::title::hitboxes
