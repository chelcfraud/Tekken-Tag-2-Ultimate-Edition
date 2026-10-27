// Regression for the native preparation stage that disabled Clive's private
// predicates before the combat evaluator could ever see them.
#include "cafe/ppc_ops.h"
#include "cafe/runtime.h"
#include "title/clive_state.h"
#include <cstdio>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <vector>

PPC_FUNC(sub_0404F398);
PPC_FUNC(sub_0404F398_orig);
PPC_FUNC(sub_0404F3D4);
PPC_FUNC(sub_0404F3D4_orig);

int main(int argc,char** argv) {
    try {
        if(argc!=2)throw std::runtime_error("expected matching Tekken.rpx");
        std::ifstream file(argv[1],std::ios::binary);
        if(!file)throw std::runtime_error("cannot read Tekken.rpx");
        const std::vector<uint8_t> rpx{std::istreambuf_iterator<char>(file),{}};
        cafe::reserve_guest_memory();cafe::load_image(rpx);
        cafe::commit_guest_memory(0x10000,0x10000);
        auto* base=cafe::guest_base();
        auto put=[&](uint32_t at,uint32_t v) { cafe::ppc::st32(base,at,v); };
        put(0x10008,0x10100);
        auto call=[&](cafe::PPCFunc* f) {
            cafe::PPCContext ctx{};ctx.r[1]=0x1f000;ctx.r[3]=0x10000;
            f(ctx,base);return ctx.r[3];
        };
        auto check=[](bool ok,const char* message) { if(!ok)throw std::runtime_error(message); };
        using namespace cafe::title::clive;
        for(auto kind:{kGaugeRequirement,kGroundedVictim,kContinuation}) {
            put(0x10100,kind);put(0x10104,200);
            put(0x10108,2);put(0x1010c,0);
            put(0x10110,46);put(0x10114,0);
            put(0x10118,690);put(0x1011c,0);
            check(call(sub_0404F398_orig)==1,"native classifier must reproduce the disabled-row bug");
            check(call(sub_0404F3D4_orig)==1,"native classifier must reproduce the special-row bug");
            check(call(sub_0404F398)==0,"private dynamic predicate must not disable the cancel");
            check(call(sub_0404F3D4)==0,"private dynamic predicate must not classify as native-only");
            // A native special condition mixed with ours still owns its flags.
            put(0x10108,660);
            check(call(sub_0404F398)==1 && call(sub_0404F3D4)==1,"native special conditions must retain their flags");
        }
        // Compare both hooks to the real title across native ids and properties.
        for(uint32_t kind=0;kind<1024;++kind) {
            put(0x10100,kind);put(0x10108,690);
            check(call(sub_0404F398)==call(sub_0404F398_orig),"native disable classification changed");
            check(call(sub_0404F3D4)==call(sub_0404F3D4_orig),"native special classification changed");
        }
        for(auto kind:{0x8001u,0x8099u,0x8f00u,0x7f03u}) {
            put(0x10100,kind);put(0x10108,690);
            check(call(sub_0404F398)==call(sub_0404F398_orig),"unrelated property/unknown requirement changed");
            check(call(sub_0404F3D4)==call(sub_0404F3D4_orig),"unrelated property/unknown classification changed");
        }
        std::puts("Clive dynamic cancels survive native preparation; native classifications unchanged");
        return 0;
    } catch(const std::exception& e) { std::fprintf(stderr,"FAIL: %s\n",e.what());return 1; }
}
