#include "title/clive_practice_menu.h"
#include <cassert>
#include <fstream>
#include <iterator>

namespace menu=cafe::title::clive::practice_menu;
menu::Node named(uint32_t tag,const char* name) { menu::Node n;n.tag=tag;n.attrs[0]=name;return n; }
menu::Node fixture() {
    menu::Node root;
    auto main=named(1,"FramePracticeMenu01");
    main.children.push_back(named(5,"SelectValuePracticeMenu02-01"));root.children.push_back(main);
    auto advanced=named(1,"FramePracticeMenu01-09");
    auto list=named(2,"MenuPracticeMenu01-09");
    list.children.push_back(named(4,"MenuItemPracticeMenu01-09-05"));advanced.children.push_back(list);
    advanced.children.push_back(named(3,"StaticPracticeDesc01-09-05"));root.children.push_back(advanced);
    auto chooser=named(1,"FramePracticeMenu02-01");
    auto choices=named(2,"MenuPracticeMenu02-01");
    choices.children.push_back(named(3,"MenuItemPracticeMenu02-01-00"));
    for(int i=1;i<=5;++i)choices.children.push_back(named(4,("MenuItemPracticeMenu02-01-0"+std::to_string(i)).c_str()));
    chooser.children.push_back(choices);root.children.push_back(chooser);return root;
}
void check(menu::Node root) {
    const auto original=root.children.size();menu::edit(root);
    auto& advanced=root.named("FramePracticeMenu01-09");
    auto& row=advanced.named("MenuPracticeMenu01-09").named(menu::kItem);
    assert(row.attrs.at(5)==menu::kLabel && !row.attrs.contains(6));
    auto& values=advanced.named(menu::kValue);
    assert(values.children.size()==5);
    for(int i=0;i<5;++i)assert(values.children[i].text==std::to_string(i+1)+std::string(1,'\0'));
    auto& chooser=root.named("FramePracticeMenu01-09-06");
    auto& choices=chooser.named("MenuPracticeMenu01-09-06");
    int levels=0;
    for(auto& n:choices.children)if(n.tag==4) {assert(n.attrs.at(5)==std::to_string(++levels));assert(!n.attrs.contains(6));}
    assert(levels==5 && root.children.size()==original+1);
    std::vector<uint8_t> once;menu::write(once,root);menu::edit(root);
    std::vector<uint8_t> twice;menu::write(twice,root);assert(once==twice);
}
int main(int argc,char** argv) {
    check(fixture());
    // Verify Xtal string sizes without touching bytecode instructions.
    menu::Node script;script.text="xtal";script.text+=char(11);
    std::vector<uint8_t> len;menu::put(len,5);script.text.append(len.begin(),len.end());script.text+="02-01";
    menu::rename(script,"02-01","01-09-06");
    assert(uint8_t(script.text[8])==8 && script.text.substr(9)=="01-09-06");
    if(argc>1) {
        std::ifstream f(argv[1],std::ios::binary);assert(f);
        std::vector<uint8_t> bytes{std::istreambuf_iterator<char>(f),{}};
        size_t p=20;auto root=menu::read(bytes,p);assert(p==menu::word(bytes,8));check(root);
        const auto patched=menu::patch(bytes);
        p=20;auto result=menu::read(patched,p);assert(p==menu::word(patched,8));
        assert(menu::word(patched,12)-menu::word(patched,8)==menu::word(bytes,12)-menu::word(bytes,8));
        assert(menu::patch(patched)==patched);
        auto& submenu=result.named("FramePracticeMenu01-09-06");
        for(const auto& n:submenu.children)if(n.tag>=100)assert(n.text.find("FramePracticeMenu01-09-09")==std::string::npos);
    }
}
