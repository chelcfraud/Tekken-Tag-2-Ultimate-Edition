#include "gpu/vulkan/renderer.h"
#include "title/clive_hud.h"
#include "cafe/runtime.h"
#include <shaderc/shaderc.h>
#include <cstring>

namespace cafe::gpu::vk {
namespace {
constexpr const char* vertex=R"(#version 460
layout(push_constant) uniform Rect { uvec2 address; ivec2 origin; ivec2 size; ivec2 extent; } rect;
void main() {
    const vec2 p[6]=vec2[6](vec2(0,0),vec2(1,0),vec2(0,1),vec2(0,1),vec2(1,0),vec2(1,1));
    vec2 xy=vec2(rect.origin)+p[gl_VertexIndex]*vec2(rect.size);
    gl_Position=vec4(xy/vec2(rect.extent)*2.0-1.0,0.0,1.0);
})";
constexpr const char* fragment=R"(#version 460
#extension GL_EXT_buffer_reference : require
#extension GL_EXT_buffer_reference_uvec2 : require
layout(buffer_reference,std430,buffer_reference_align=4) readonly buffer Pixels { uint rgba[]; };
layout(push_constant) uniform Rect { uvec2 address; ivec2 origin; ivec2 size; ivec2 extent; } rect;
layout(location=0) out vec4 color;
void main() {
    ivec2 xy=clamp(ivec2(gl_FragCoord.xy)-rect.origin,ivec2(0),rect.size-1);
    color=unpackUnorm4x8(Pixels(rect.address).rgba[xy.y*rect.size.x+xy.x]);
})";
}

void Renderer::draw_clive_numerals(const Image& scan) {
    namespace hud=title::clive::hud;
    const auto now=hud::now_ms();
    for(unsigned slot=0;slot<4;++slot) {
        const auto state=hud::snapshot(slot,now);
        if(!state.visible || !state.on_field)continue;
        if(numeral_layout_==VK_NULL_HANDLE) {
            VkPushConstantRange push{VK_SHADER_STAGE_VERTEX_BIT|VK_SHADER_STAGE_FRAGMENT_BIT,0,32};
            VkPipelineLayoutCreateInfo info{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
            info.pushConstantRangeCount=1;info.pPushConstantRanges=&push;
            VK_CHECK(vkCreatePipelineLayout(ctx_.device,&info,nullptr,&numeral_layout_));
        }
        auto& pipeline=numeral_pipelines_[scan.format];
        if(pipeline==VK_NULL_HANDLE) {
            auto compile=[&](const char* source,shaderc_shader_kind kind) {
                auto options=shaderc_compile_options_initialize();
                shaderc_compile_options_set_target_env(options,shaderc_target_env_vulkan,shaderc_env_version_vulkan_1_3);
                auto result=shaderc_compile_into_spv(compiler_,source,std::strlen(source),kind,"Clive numeral","main",options);
                shaderc_compile_options_release(options);
                if(shaderc_result_get_compilation_status(result)!=shaderc_compilation_status_success)
                    fatal("Vulkan: numeral shader: %s",shaderc_result_get_error_message(result));
                VkShaderModuleCreateInfo info{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};
                info.codeSize=shaderc_result_get_length(result);
                info.pCode=reinterpret_cast<const uint32_t*>(shaderc_result_get_bytes(result));
                VkShaderModule module;
                VK_CHECK(vkCreateShaderModule(ctx_.device,&info,nullptr,&module));
                shaderc_result_release(result);return module;
            };
            const VkShaderModule vs=compile(vertex,shaderc_vertex_shader),ps=compile(fragment,shaderc_fragment_shader);
            VkPipelineShaderStageCreateInfo stages[2]{};
            for(auto& stage:stages) { stage.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;stage.pName="main"; }
            stages[0].stage=VK_SHADER_STAGE_VERTEX_BIT;stages[0].module=vs;
            stages[1].stage=VK_SHADER_STAGE_FRAGMENT_BIT;stages[1].module=ps;
            VkPipelineVertexInputStateCreateInfo vi{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
            VkPipelineInputAssemblyStateCreateInfo ia{VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO};
            ia.topology=VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
            VkPipelineViewportStateCreateInfo vp{VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO};
            vp.viewportCount=1;vp.scissorCount=1;
            VkPipelineRasterizationStateCreateInfo rs{VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO};
            rs.polygonMode=VK_POLYGON_MODE_FILL;rs.lineWidth=1;
            VkPipelineMultisampleStateCreateInfo ms{VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO};
            ms.rasterizationSamples=VK_SAMPLE_COUNT_1_BIT;
            VkPipelineColorBlendAttachmentState blend{};
            blend.blendEnable=VK_TRUE;blend.colorWriteMask=0xf;
            blend.srcColorBlendFactor=VK_BLEND_FACTOR_SRC_ALPHA;blend.dstColorBlendFactor=VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
            blend.colorBlendOp=blend.alphaBlendOp=VK_BLEND_OP_ADD;
            blend.srcAlphaBlendFactor=VK_BLEND_FACTOR_ONE;blend.dstAlphaBlendFactor=VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
            VkPipelineColorBlendStateCreateInfo cb{VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO};
            cb.attachmentCount=1;cb.pAttachments=&blend;
            const VkDynamicState states[]={VK_DYNAMIC_STATE_VIEWPORT,VK_DYNAMIC_STATE_SCISSOR};
            VkPipelineDynamicStateCreateInfo dynamic{VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO};
            dynamic.dynamicStateCount=2;dynamic.pDynamicStates=states;
            VkPipelineRenderingCreateInfo rendering{VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO};
            rendering.colorAttachmentCount=1;rendering.pColorAttachmentFormats=&scan.format;
            VkGraphicsPipelineCreateInfo info{VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO};
            info.pNext=&rendering;info.stageCount=2;info.pStages=stages;
            info.pVertexInputState=&vi;info.pInputAssemblyState=&ia;info.pViewportState=&vp;
            info.pRasterizationState=&rs;info.pMultisampleState=&ms;info.pColorBlendState=&cb;
            info.pDynamicState=&dynamic;info.layout=numeral_layout_;
            VK_CHECK(vkCreateGraphicsPipelines(ctx_.device,pipeline_cache_,1,&info,nullptr,&pipeline));
            vkDestroyShaderModule(ctx_.device,vs,nullptr);vkDestroyShaderModule(ctx_.device,ps,nullptr);
        }
        const auto image=hud::raster(state,std::max(1u,scan.width/1280));
        const auto pos=hud::position(slot,scan.width,scan.height,image.width);
        if(pos.x+image.width>scan.width || pos.y+image.height>scan.height)continue;
        VkDeviceSize offset=0;
        std::memcpy(upload(image.pixels.size(),4,offset),image.pixels.data(),image.pixels.size());
        barrier();
        VkRenderingAttachmentInfo attachment{VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO};
        attachment.imageView=scan.view;attachment.imageLayout=VK_IMAGE_LAYOUT_GENERAL;
        attachment.loadOp=VK_ATTACHMENT_LOAD_OP_LOAD;attachment.storeOp=VK_ATTACHMENT_STORE_OP_STORE;
        VkRenderingInfo rendering{VK_STRUCTURE_TYPE_RENDERING_INFO};
        rendering.renderArea.extent={scan.width,scan.height};rendering.layerCount=1;
        rendering.colorAttachmentCount=1;rendering.pColorAttachments=&attachment;
        const auto c=cmd();vkCmdBeginRendering(c,&rendering);
        vkCmdBindPipeline(c,VK_PIPELINE_BIND_POINT_GRAPHICS,pipeline);
        const VkViewport viewport{0,0,float(scan.width),float(scan.height),0,1};
        const VkRect2D scissor{{int32_t(pos.x),int32_t(pos.y)},{image.width,image.height}};
        vkCmdSetViewport(c,0,1,&viewport);vkCmdSetScissor(c,0,1,&scissor);
        const uint64_t address=ring_.address()+offset;
        const uint32_t push[]={uint32_t(address),uint32_t(address>>32),pos.x,pos.y,
            image.width,image.height,scan.width,scan.height};
        vkCmdPushConstants(c,numeral_layout_,VK_SHADER_STAGE_VERTEX_BIT|VK_SHADER_STAGE_FRAGMENT_BIT,0,sizeof(push),push);
        vkCmdDraw(c,6,1,0,0);vkCmdEndRendering(c);
        bound_pipeline_=nullptr;barrier();
    }
}
}
