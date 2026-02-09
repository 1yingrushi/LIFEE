(() => {
  // Help view (extracted from index.html)
  const html = htm.bind(React.createElement);
  window.LIFEE_VIEWS = window.LIFEE_VIEWS || {};

  window.LIFEE_VIEWS.help = ({ onBack }) => {
    return html`
      <div className="p-6 md:p-12 max-w-[900px] mx-auto animate-in space-y-8">
        <div className="flex items-center justify-between">
          <button
            onClick=${onBack}
            className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest opacity-40 hover:opacity-100 transition-all"
          >
            <${Icon} name="ChevronLeft" size=${14} /> Back
          </button>
          <h2 className="text-2xl md:text-4xl font-serif italic tracking-tight text-[#1A1A1A]">Help</h2>
          <div className="w-14" />
        </div>
        <div className="bg-white rounded-[36px] border border-[#F0EDEA] p-6 md:p-10 shadow-sm space-y-6">
          <div className="text-[10px] font-black uppercase tracking-[0.25em] opacity-40">Quick guide</div>
          <div className="space-y-4 text-sm leading-relaxed">
            <div>
              <div className="font-bold text-[#1A1A1A] mb-1">如何开始对话？</div>
              <div className="opacity-70">在首页填写情境并邀请至少 2 个 Voices，然后点击底部的 “Commence Dialogue”。</div>
            </div>
            <div>
              <div className="font-bold text-[#1A1A1A] mb-1">如何更换 Persona 头像？</div>
              <div className="opacity-70">进入某个 Persona 的二级页面：左侧“卡片背景”用于上传背景图；点击下方的头像 icon 会弹出“Icon 编辑”，用于上传/选择 icon（用于列表左上角）。</div>
            </div>
            <div>
              <div className="font-bold text-[#1A1A1A] mb-1">如何导出聊天记录？</div>
              <div className="opacity-70">进入 Settings → Share chat history，可复制或下载。</div>
            </div>
          </div>
          <div className="pt-4 border-t border-[#F0EDEA] text-xs opacity-60">
            如需更详细的帮助内容，可以继续在 <code className="px-1 py-0.5 rounded bg-[#FDFBF7] border border-[#F0EDEA]">web/ui/data/navigation.js</code> 扩展成更多条目。
          </div>
        </div>
      </div>
    `;
  };
})();

