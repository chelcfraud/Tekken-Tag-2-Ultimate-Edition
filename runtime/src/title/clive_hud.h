#pragma once
#include "title/clive_state.h"
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <memory>
#include <mutex>
#include <span>
#include <stdexcept>
#include <vector>

namespace cafe::title::clive::hud {
inline std::array<std::atomic<uint64_t>,4> actors{};
inline uint64_t now_ms() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}
inline void publish(unsigned slot,int points,bool present,bool on_field,uint64_t now=now_ms()) {
    if(slot<actors.size())actors[slot].store((now<<16) | uint64_t(std::clamp(points,0,200)) |
        (present ? 256u : 0u) | (on_field ? 512u : 0u),std::memory_order_release);
}
struct Value { bool visible=false,on_field=false; unsigned points=0; };
inline Value snapshot(unsigned slot,uint64_t now=now_ms()) {
    if(slot>=actors.size())return {};
    const auto data=actors[slot].load(std::memory_order_acquire),stamp=data>>16;
    return {(data&256)!=0 && now>=stamp && now-stamp<750,(data&512)!=0,unsigned(data&255)};
}
struct Digits { unsigned width=0,height=0; std::vector<uint8_t> alpha; };
class DigitStore {
    mutable std::mutex mutex;
    std::shared_ptr<const Digits> value;
public:
    void store(std::shared_ptr<const Digits> v,std::memory_order = std::memory_order_seq_cst) {
        std::lock_guard lock(mutex);value=std::move(v);
    }
    std::shared_ptr<const Digits> load(std::memory_order = std::memory_order_seq_cst) const {
        std::lock_guard lock(mutex);return value;
    }
};
inline DigitStore digits;
inline std::shared_ptr<const Digits> read(std::span<const uint8_t> data) {
    auto word=[&](size_t at) {
        if(at+4>data.size())throw std::runtime_error("truncated numeral atlas");
        return uint32_t(data[at])|uint32_t(data[at+1])<<8|uint32_t(data[at+2])<<16|uint32_t(data[at+3])<<24;
    };
    if(word(0)!=0x4455485a || word(4)!=1)throw std::runtime_error("unsupported numeral atlas");
    const auto w=word(8),h=word(12);
    if(w<8 || h<8 || w>256 || h>256 || data.size()!=16+size_t(w)*h*5)
        throw std::runtime_error("invalid numeral atlas dimensions");
    return std::make_shared<Digits>(Digits{w,h,{data.begin()+16,data.end()}});
}
struct Image { unsigned width=0,height=0; std::vector<uint8_t> pixels; };
inline Image raster(Value value,unsigned scale=1,bool bgra=false) {
    scale=std::clamp(scale,1u,8u);
    const unsigned glyph=32*scale;
    Image image{glyph,38*scale,{}};
    image.pixels.resize(size_t(image.width)*image.height*4);
    const unsigned level=std::min(4u,value.points/50);
    const auto atlas=digits.load(std::memory_order_acquire);
    static constexpr std::array<std::array<unsigned,7>,5> fallback{{
        {4,12,4,4,4,4,14},{14,17,1,2,4,8,31},{30,1,1,14,1,1,30},
        {2,6,10,18,31,2,2},{31,16,16,30,1,1,30}}};
    auto alpha=[&](unsigned x,unsigned y) {
        if(!atlas) {
            const unsigned row=std::min(6u,y*7/glyph),col=std::min(4u,x*5/glyph);
            return (fallback[level][row]&(16u>>col)) ? 255u : 0u;
        }
        const float sx=(x+.5f)*atlas->width/glyph-.5f,sy=(y+.5f)*atlas->height/glyph-.5f;
        const int left=int(std::floor(sx)),top=int(std::floor(sy));
        const float fx=sx-left,fy=sy-top;
        auto at=[&](int xx,int yy) { return float(atlas->alpha[(size_t(level)*atlas->height+
            std::clamp(yy,0,int(atlas->height)-1))*atlas->width+std::clamp(xx,0,int(atlas->width)-1)]); };
        return unsigned(std::clamp((1-fy)*((1-fx)*at(left,top)+fx*at(left+1,top))+
            fy*((1-fx)*at(left,top+1)+fx*at(left+1,top+1)),0.f,255.f));
    };
    for(unsigned y=0;y<glyph;++y)for(unsigned x=0;x<image.width;++x) {
        auto* p=&image.pixels[(size_t(y)*image.width+x)*4];
        const std::array<uint8_t,3> ink=level==4 ? std::array<uint8_t,3>{255,217,140} : std::array<uint8_t,3>{245,240,255};
        p[0]=ink[bgra?2:0];p[1]=ink[1];p[2]=ink[bgra?0:2];p[3]=uint8_t(alpha(x,y));
    }
    // Progress towards the next numeral; level five keeps the gold bar full.
    // Leave the original glyph and its screen position unchanged.
    const unsigned progress=value.points>=200 ? 50 : value.points%50;
    for(unsigned y=34*scale;y<36*scale;++y)for(unsigned x=4*scale;x<28*scale;++x) {
        const bool filled=(x-4*scale)*50<24*scale*progress;
        const std::array<uint8_t,3> ink=filled ?
            (level==4 ? std::array<uint8_t,3>{255,217,140} : std::array<uint8_t,3>{245,240,255}) :
            std::array<uint8_t,3>{40,32,48};
        auto* p=&image.pixels[(size_t(y)*image.width+x)*4];
        p[0]=ink[bgra?2:0];p[1]=ink[1];p[2]=ink[bgra?0:2];p[3]=filled ? 255 : 190;
    }
    return image;
}
struct Position { unsigned x,y; };
inline Position position(unsigned slot,unsigned width,unsigned height,unsigned glyph_width) {
    const unsigned inset=width*28/100;
    return {slot%2 ? width-inset-glyph_width : inset,height*14/100};
}
}
