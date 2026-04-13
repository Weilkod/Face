export default function Footer() {
  return (
    <footer className="border-t border-black/5 bg-white py-10">
      <div className="mx-auto max-w-3xl px-4 text-center">
        <p className="text-[11px] leading-relaxed text-ink-muted">
          ⚠️ 본 서비스는 100% 엔터테인먼트 목적으로 제작되었습니다.
          <br />
          관상 및 운세 분석은 과학적 근거가 없으며, 실제 경기 결과 예측 또는
          스포츠 베팅의 참고 자료로 활용될 수 없습니다.
        </p>
        <p className="mt-4 text-[10px] font-semibold tracking-widest text-coral">
          FACEMETRICS · 2026
        </p>
      </div>
    </footer>
  );
}
