#pragma once
#include <algorithm>
#include <cstdint>

namespace cafe::title::clive {
constexpr uint32_t kGaugeRequirement=0x7f00;
constexpr uint32_t kGroundedVictim=0x7f01;
constexpr uint32_t kContinuation=0x7f02;
constexpr uint32_t kHeldCharge=0x7f03, kChargeBegin=0x8f04;
constexpr uint32_t kGuardBroken=0x8f05;
constexpr uint32_t kGain=0x8f00, kReset=0x8f01, kContactGain=0x8f02,kBegin=0x8f03;
// Native requirement 314: lwz r0,216(r25), r25=player+288.
// This is the second captured-contact variable, not a whole evaluator call.
constexpr uint32_t kContactVariable=0x1f8;
constexpr uint32_t kVictimHitLevel=0x130;
inline bool grounded_victim(uint32_t hitlevel) {
    const auto level=hitlevel&0x407;
    return level==1 || level==2; // native requirements 64 and 63 respectively
}
struct Gauge {
    int points=0;
    int attack_points=0;
    void add(int32_t amount) { points=int(std::clamp<int64_t>(int64_t(points)+amount,0,200)); }
    bool at_least(uint32_t amount) const { return amount<=200 && points>=int(amount); }
    unsigned level() const { return 1+unsigned(points/50); }
    void set_level(unsigned level) { points=50*int(std::clamp(level,1u,5u)-1);attack_points=points; }
};
struct Charge {
    uint32_t move=0, deadline=0, opponent=0;
    bool held=false, complete=false, broken=false;
    void begin(uint32_t current,uint32_t until,bool lp) { *this={};move=current;deadline=until;held=lp; }
    void update(uint32_t current,uint32_t frame,bool lp) {
        if(current!=move) { *this={};return; }
        if(!move || complete)return;
        held=held && lp;
        if(frame>=deadline)complete=true;
    }
    bool ready(const Gauge& gauge,uint32_t current,uint32_t threshold) const {
        // Keep the confirmed attack's reaction stable after paying its cost.
        return move && current==move && held && complete && threshold==200 && (broken || gauge.at_least(threshold));
    }
    bool confirm_guard_break(Gauge& gauge,uint32_t current,uint32_t victim) {
        if(!victim || opponent!=victim || broken || !ready(gauge,current,200))return false;
        gauge.set_level(4);broken=true;
        return true;
    }
};
inline void property(Gauge& gauge,uint32_t id,uint32_t value,uint32_t captured_contact) {
    if(id==kReset)gauge=Gauge{};
    else if(id==kBegin)gauge.attack_points=gauge.points;
    else if(id==kGain)gauge.add(static_cast<int32_t>(value));
    else if(id==kContactGain) {
        const auto wanted=value>>16;
        if((wanted==1 || wanted==2) && captured_contact==wanted)gauge.add(value&0xffff);
    }
}
inline bool continuation(const Gauge& gauge,uint32_t threshold) {
    return threshold<=200 && gauge.attack_points>=int(threshold);
}
inline bool runtime_requirement(uint32_t kind) {
    return kind==kGaugeRequirement || kind==kGroundedVictim || kind==kContinuation || kind==kHeldCharge;
}
// 0404F398/0404F3D4 classify native special requirements before combat.
// Their flag 2 disables a row in 0414E7E4. Our runtime predicates are dynamic
// conditions, not native special requirements, despite their private ids.
inline bool native_special_requirement(uint32_t kind,uint32_t first) {
    return !runtime_requirement(kind) && kind>=first && !(kind&0x8000);
}
}
