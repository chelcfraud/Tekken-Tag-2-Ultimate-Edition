// Exercise the original title's collision primitive with synthetic blade and
// hurt-capsule coordinates. This does not certify a fighter's imported data.
#include "cafe/ppc_ops.h"
#include "cafe/runtime.h"
#include "title/imported_hitboxes.h"
#include <zlib.h>
#include <array>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <vector>

PPC_FUNC(sub_039C006C);

int main(int argc, char** argv) {
    try {
        if (argc != 2 && argc != 4) throw std::runtime_error("expected Tekken.rpx [fighter.hitboxes fighter.moveset]");
        std::ifstream file(argv[1], std::ios::binary);
        if (!file) throw std::runtime_error("cannot read Tekken.rpx");
        const std::vector<uint8_t> rpx{std::istreambuf_iterator<char>(file), {}};
        cafe::reserve_guest_memory();
        cafe::load_image(rpx);
        cafe::commit_guest_memory(0x10000, 0x10000);
        auto* base = cafe::guest_base();
        auto put = [&](uint32_t at, const std::array<float,6>& values) {
            for (size_t n=0; n<values.size(); ++n)
                cafe::ppc::st32(base, at+4*n, cafe::ppc::store_single(values[n]));
        };
        auto collision = [&](std::array<float,6> blade, std::array<float,6> body, double thickness=0.) {
            put(0x10000, blade);
            put(0x10100, body);
            cafe::PPCContext ctx{};
            ctx.r[1]=0x1f000;
            ctx.r[3]=0x10000;
            ctx.r[4]=0x10100;
            ctx.f[1]={thickness,thickness};
            sub_039C006C(ctx, base);
            return ctx.r[3]!=0;
        };
        auto check = [](bool condition, const char* message) {
            if (!condition) throw std::runtime_error(message);
        };
        // Native hurt shape: centre XYZ, vertical half-height, radius squared,
        // twice the radius (039C006C combines the latter two with blade radius).
        constexpr std::array<float,6> body{0,1000,750,200,10000,200};
        check(collision({0,1000,0,0,1000,1150},body), "blade must reach beyond the fist");
        check(!collision({0,1000,0,0,1000,200},body), "fist must not inherit blade reach");
        check(!collision({300,1000,0,300,1000,1150},body), "lateral blade miss must remain a miss");
        check(!collision({0,1500,0,0,1500,1150},body), "blade above the body must miss");
        check(collision({0,1100,750,0,1100,750},body), "stationary point inside body must hit");
        check(!collision({0,1000,-100,0,1000,-200},body), "blade behind attacker must not hit in front");
        check(!collision({150,1000,0,150,1000,1150},body), "thin blade must miss outside body radius");
        check(collision({150,1000,0,150,1000,1150},body,60), "explicit blade radius must extend contact");
        namespace hb=cafe::title::hitboxes;
        // An advancing actor must carry the sword into the follow-up. Baking
        // its world frame before the actor moves leaves the blade out of range.
        const hb::Frame local_grip{{0,1000,0},{{{1,0,0},{0,0,1},{0,-1,0}}}};
        const hb::Frame advanced_parent{{0,0,600},{{{1,0,0},{0,1,0},{0,0,1}}}};
        const auto advanced_grip=hb::compose(local_grip,advanced_parent);
        const auto advanced_tip=hb::transform(advanced_grip,{0,1000,0});
        constexpr std::array<float,6> retreated_body{0,1000,1500,200,10000,200};
        check(collision({advanced_grip.origin[0],advanced_grip.origin[1],advanced_grip.origin[2],
                         advanced_tip[0],advanced_tip[1],advanced_tip[2]},retreated_body),
            "follow-up blade must use the parent's current advancement");
        check(!collision({0,1000,0,0,1000,1000},retreated_body),
            "stale world frame must reproduce the follow-up range regression");
        const hb::Frame grip{{0,1000,0},{{{1,0,0},{0,0,1},{0,-1,0}}}};
        auto point=[](uint32_t)->std::optional<hb::Vec> { return hb::Vec{0,1000,0}; };
        auto frame=[&](uint32_t)->std::optional<hb::Frame> { return grip; };
        hb::Endpoint tip;tip.kind=2;tip.a=4;tip.offset_a={0,1000,0};
        hb::Endpoint handle=tip;handle.offset_a={0,0,0};
        const auto a=hb::position(tip,point,frame,frame,0),b=hb::position(handle,point,frame,frame,0);
        check(a && b,"weapon endpoints must have valid frames");
        const auto line=hb::segment(*a,*b,*a,0,false);
        check(collision({line.a[0],line.a[1],line.a[2],line.b[0],line.b[1],line.b[2]},body),
            "zero-radius sword offsets must hit beyond the hand (f+1+2 first hit)");
        tip.a=5;tip.offset_a={0,900,0};
        const auto back_one=hb::position(tip,point,frame,frame,0);
        check(back_one && (*back_one)[2]==900,"b+1 must retain its authored grip offset");
        check(collision({0,1000,0,(*back_one)[0],(*back_one)[1],(*back_one)[2]},body),
            "b+1 segment must reach its opponent");
        const auto swept=hb::segment({0,1000,1000},{0,1000,1000},{0,1000,500},0,true);
        check(collision({swept.a[0],swept.a[1],swept.a[2],swept.b[0],swept.b[1],swept.b[2]},body),
            "single-point attacks must sweep across the previous pose");
        const auto vertical=hb::segment({0,1000,750},{0,1000,0},{0,1000,0},400,true);
        check(vertical.a[1]==1200 && vertical.b[1]==800 && vertical.b[2]==750,
            "height must create a vertical capsule instead of a sweep");
        hb::Shape first;first.first=16;first.last=17;
        hb::Shape second;second.first=36;second.last=36;
        check(first.active(16) && !second.active(16) && !first.active(36) && second.active(36),
            "both attack windows must retain their own active frames");
        const hb::Frame root{{200,900,300},{{{2,0,0},{0,2,0},{0,0,2}}}};
        auto root_frame=[&](uint32_t)->std::optional<hb::Frame> { return root; };
        hb::Endpoint plane;plane.kind=4;plane.offset_a={50,100,400};
        const auto grounded=hb::position(plane,point,root_frame,frame,-200);
        check(grounded && *grounded==hb::Vec{250,-100,700},
            "ground-relative offsets must ignore root height and model scale");
        auto limb_point=[](uint32_t index)->std::optional<hb::Vec> { return hb::Vec{float(index)*100,1000,0}; };
        hb::Endpoint midpoint;midpoint.kind=3;midpoint.a=1;midpoint.b=2;
        const auto middle=hb::position(midpoint,limb_point,root_frame,frame,0);
        check(middle && (*middle)[0]==150,"virtual limb midpoint must remain between its two joints");
        // Asset-free binary contract: a swept sword shape with a 1000 mm offset.
        std::vector<uint8_t> fixture;
        auto word=[&](uint32_t v) { for(int i=0;i<4;++i)fixture.push_back(uint8_t(v>>(8*i))); };
        for(uint32_t v:{0x42483854u,1u,123u,1u,0x520001u,1u,16u,17u,0u,0u})word(v);
        for(uint32_t v:{2u,4u,0u,0u,0u})word(v);
        for(float v:{0.f,1000.f,0.f,0.f,0.f,0.f})word(std::bit_cast<uint32_t>(v));
        for(uint32_t v:{5u,0u,0u,0u,0u,0u,0u,0u,0u,0u,0u})word(v);
        const auto decoded=hb::read(fixture,123);
        check(decoded.at(0x520001).at(0).a.offset_a[1]==1000,
            "binary sidecar must retain the complete blade offset");
        auto rejected=[&](std::vector<uint8_t> bytes,uint32_t crc) {
            try { hb::read(bytes,crc); } catch(const std::runtime_error&) { return true; }
            return false;
        };
        check(rejected(fixture,124),"a different moveset CRC must be refused");
        auto cut=fixture;cut.pop_back();check(rejected(cut,123),"truncated shapes must be refused");
        auto nan=fixture;
        const size_t offset_y=16+8+16+20+4;
        const uint32_t not_finite=0x7fc00000u;
        for(int i=0;i<4;++i)nan[offset_y+i]=uint8_t(not_finite>>(8*i));
        check(rejected(nan,123),"non-finite collision offsets must be refused");
        if(argc==4) {
            auto bytes=[](const char* path) {
                std::ifstream f(path,std::ios::binary);
                if(!f)throw std::runtime_error("cannot read collision fixture");
                return std::vector<uint8_t>{std::istreambuf_iterator<char>(f),{}};
            };
            auto shapes=bytes(argv[2]),moves=bytes(argv[3]);
            const uint32_t crc=crc32(0,moves.data(),moves.size());
            const auto imported=hb::read(shapes,crc);
            check(!imported.empty(),"real imported collision moves must not be empty");
            bool refused=false;
            try { hb::read(shapes,crc^1); } catch(const std::runtime_error&) { refused=true; }
            check(refused,"collision metadata must reject a different moveset");
            shapes.pop_back();refused=false;
            try { hb::read(shapes,crc); } catch(const std::runtime_error&) { refused=true; }
            check(refused,"truncated collision metadata must be rejected");
            std::printf("Validated full collision sidecar for %zu real imported moves\n",imported.size());
        }
        std::puts("Native collision distinguishes blade reach, fist reach, vertical/lateral misses and radius");
        return 0;
    } catch (const std::exception& error) {
        std::fprintf(stderr,"FAIL: %s\n",error.what());
        return 1;
    }
}
