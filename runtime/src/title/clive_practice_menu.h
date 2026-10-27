#pragma once
#include <cstdint>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace cafe::title::clive::practice_menu {
constexpr uint32_t kResource = 0xe23e4d32;
constexpr const char* kValue = "SelectValuePracticeMenu01-09-06";
constexpr const char* kItem = "MenuItemPracticeMenu01-09-06";
constexpr const char* kLabel = "Clive Enhanced State";
struct Node {
    uint32_t tag = 0;
    std::string text;
    std::map<uint32_t, std::string> attrs;
    std::vector<Node> children;
    std::string name() const { auto i=attrs.find(0); return i==attrs.end()?"":i->second; }
    Node& named(const std::string& name) {
        for(auto& child:children) if(child.name()==name)return child;
        throw std::runtime_error("missing practice menu node: "+name);
    }
};
inline uint32_t word(const std::vector<uint8_t>& d,size_t p) {
    if(p>d.size() || d.size()-p<4)throw std::runtime_error("truncated practice menu");
    return uint32_t(d[p])<<24|uint32_t(d[p+1])<<16|uint32_t(d[p+2])<<8|d[p+3];
}
inline void put(std::vector<uint8_t>& d,uint32_t v) {
    for(int s=24;s>=0;s-=8)d.push_back(uint8_t(v>>s));
}
inline std::string string(const std::vector<uint8_t>& d,size_t& p) {
    size_t n=word(d,p);p+=4;
    if(n>d.size()-p)throw std::runtime_error("truncated practice menu string");
    std::string s(d.begin()+p,d.begin()+p+n);p=(p+n+3)&~size_t(3);
    return s;
}
inline Node read(const std::vector<uint8_t>& d,size_t& p,unsigned depth=0) {
    if(depth>32)throw std::runtime_error("practice menu nesting");
    Node n;n.tag=word(d,p);p+=4;n.text=string(d,p);
    uint32_t count=word(d,p);p+=4;
    if(count>128)throw std::runtime_error("practice menu attributes");
    while(count--) { auto key=word(d,p);p+=4;auto s=string(d,p);if(!s.empty() && s.back()==0)s.pop_back();n.attrs[key]=s; }
    count=word(d,p);p+=4;
    if(count>2048)throw std::runtime_error("practice menu children");
    while(count--)n.children.push_back(read(d,p,depth+1));
    return n;
}
inline void write_string(std::vector<uint8_t>& d,const std::string& s) {
    put(d,uint32_t(s.size()));d.insert(d.end(),s.begin(),s.end());while(d.size()%4)d.push_back(0);
}
inline void write(std::vector<uint8_t>& d,const Node& n) {
    put(d,n.tag);write_string(d,n.text);put(d,uint32_t(n.attrs.size()));
    for(const auto& [key,value]:n.attrs) { put(d,key);write_string(d,value+std::string(1,'\0')); }
    put(d,uint32_t(n.children.size()));for(const auto& c:n.children)write(d,c);
}
inline void replace(std::string& s,const std::string& from,const std::string& to) {
    size_t p=0;while((p=s.find(from,p))!=std::string::npos) { s.replace(p,from.size(),to);p+=to.size(); }
}
// Xtal's code is followed by serialized strings (type 11/14, BE length,
// bytes). Rename those constants, preserving every instruction and index.
inline void rename(Node& n,const std::string& from,const std::string& to) {
    for(auto& [key,value]:n.attrs)replace(value,from,to);
    if(n.text.starts_with("xtal")) {
        auto& s=n.text;
        for(size_t p=0;p+5<=s.size();++p) {
            if(uint8_t(s[p])!=11 && uint8_t(s[p])!=14)continue;
            uint32_t len=0;for(int i=1;i<=4;++i)len=(len<<8)|uint8_t(s[p+i]);
            if(len>s.size()-p-5)continue;
            auto value=s.substr(p+5,len);
            if(value.find(from)==std::string::npos)continue;
            replace(value,from,to);
            s.replace(p+5,len,value);
            for(int i=0;i<4;++i)s[p+1+i]=char(uint32_t(value.size())>>(24-8*i));
            p+=4+value.size();
        }
    }
    for(auto& c:n.children)rename(c,from,to);
}
inline void label(Node& n,const std::string& text) { n.attrs.erase(6);n.attrs.erase(12);n.attrs[5]=text; }
inline void edit(Node& root) {
    auto& advanced=root.named("FramePracticeMenu01-09");
    auto& menu=advanced.named("MenuPracticeMenu01-09");
    for(const auto& n:menu.children)if(n.name()==kItem)return;
    auto row=menu.named("MenuItemPracticeMenu01-09-05");
    rename(row,"01-09-05","01-09-06");label(row,kLabel);row.attrs[8]="1";
    menu.children.push_back(row);
    auto value=root.named("FramePracticeMenu01").named("SelectValuePracticeMenu02-01");
    value.attrs[0]=kValue;value.children.clear();
    for(int i=1;i<=5;++i) { Node n;n.tag=6;n.text=std::to_string(i)+std::string(1,'\0');if(i==1)n.attrs[14]="true";value.children.push_back(n); }
    advanced.children.push_back(value);
    auto desc=advanced.named("StaticPracticeDesc01-09-05");rename(desc,"01-09-05","01-09-06");
    label(desc,"Set Clive's enhanced state level from 1 to 5.");advanced.children.push_back(desc);
    auto submenu=root.named("FramePracticeMenu02-01");
    // Return to Advanced Settings when confirming or cancelling this chooser.
    rename(submenu,"FramePracticeMenu01", "FramePracticeMenu01-09");
    rename(submenu,"02-01","01-09-06");rename(submenu,"02_01","01_09_06");
    auto& choices=submenu.named("MenuPracticeMenu01-09-06");
    for(auto& n:choices.children) {
        if(n.tag==3)label(n,kLabel);
        if(n.tag==4) { auto name=n.name();label(n,std::to_string(name.back()-'0')); }
    }
    for(auto& n:submenu.children)if(n.tag==3 && n.name().starts_with("StaticPracticeDesc"))label(n,"Set Clive's enhanced state level from 1 to 5.");
    root.children.push_back(submenu);
}
inline std::vector<uint8_t> patch(const std::vector<uint8_t>& input) {
    if(word(input,0)!=0x42583031 || word(input,16)!=1)throw std::runtime_error("unsupported practice menu");
    const size_t tags=word(input,8),attrs=word(input,12);
    size_t p=20;auto root=read(input,p);
    if(p!=tags || tags>attrs || attrs>input.size())throw std::runtime_error("invalid practice menu tables");
    edit(root);
    std::vector<uint8_t> out(input.begin(),input.begin()+8);put(out,0);put(out,0);put(out,1);write(out,root);
    const auto new_tags=uint32_t(out.size()),new_attrs=new_tags+uint32_t(attrs-tags);
    out.insert(out.end(),input.begin()+tags,input.end());
    for(int i=0;i<4;++i) {out[8+i]=uint8_t(new_tags>>(24-8*i));out[12+i]=uint8_t(new_attrs>>(24-8*i));}
    return out;
}
}
