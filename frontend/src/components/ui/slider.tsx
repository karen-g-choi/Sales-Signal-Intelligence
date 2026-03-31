interface SliderProps {
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
}

export function Slider({ value, min, max, step = 1, onChange }: SliderProps) {
  return (
    <input
      type="range"
      value={value}
      min={min}
      max={max}
      step={step}
      onChange={(event) => onChange(Number(event.target.value))}
      className="h-2 w-full cursor-pointer appearance-none rounded-full bg-lightslate accent-navy"
    />
  );
}
