import TickerInput from '../components/TickerInput';
import useLang from '../hooks/useLang';

export default function Home() {
  const [lang] = useLang();

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="max-w-xl mx-auto px-6 text-center">
        <h1 className="text-4xl font-serif font-bold text-white mb-4">
          {lang === 'zh' ? <>用大师的眼光<br />看每一只股票</> : <>See every stock<br />through the eyes of the masters</>}
        </h1>
        <p className="text-gray-400 mb-8">
          {lang === 'zh'
            ? '输入股票代码，60秒获得巴菲特、格雷厄姆、林奇等10位大师的独立裁决'
            : 'Enter a ticker and get independent verdicts from Buffett, Graham, Lynch and 7 other legendary investors in 60 seconds'}
        </p>
        <TickerInput />
        <p className="text-xs text-gray-600 mt-4">
          {lang === 'zh'
            ? '支持美股 · 港股 | 教育性内容，非投资建议'
            : 'Covers US & HK markets | Educational content, not investment advice'}
        </p>
      </div>
    </div>
  );
}
