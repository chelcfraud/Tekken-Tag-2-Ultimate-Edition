// Exercise the original title's collision primitive with synthetic blade and
// hurt-capsule coordinates. This does not certify a fighter's imported data.
#include "cafe/ppc_ops.h"
#include "cafe/runtime.h"
#include <array>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <vector>

PPC_FUNC(sub_039C006C);

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::runtime_error("expected the matching Tekken.rpx path");
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
        std::puts("Native collision distinguishes blade reach, fist reach, vertical/lateral misses and radius");
        return 0;
    } catch (const std::exception& error) {
        std::fprintf(stderr,"FAIL: %s\n",error.what());
        return 1;
    }
}
