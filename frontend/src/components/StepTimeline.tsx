import { useTranslation } from "react-i18next";

import type { ApplicationFile, Step } from "../api/types";
import { formatShortDate } from "./format";
import { IconCheck } from "./icons";

export const STEPS: Step[] = ["draft", "appointment", "documents", "submitted", "decided"];

export function StepTimeline({ file }: { file: ApplicationFile }) {
  const { t, i18n } = useTranslation();
  const current = STEPS.indexOf(file.step);
  const reachedAt = new Map(file.events.map((event) => [event.step, event.occurred_at]));
  // The track runs between the centres of the first and last dots (10 % … 90 %).
  const fill = (current / (STEPS.length - 1)) * 80;

  return (
    <div className="relative">
      <div aria-hidden="true" className="absolute top-[13px] right-[10%] left-[10%] h-0.5 bg-line" />
      <div
        aria-hidden="true"
        className="va-grow absolute top-[13px] left-[10%] h-0.5 bg-brand"
        style={{ width: `${fill}%` }}
      />
      <ol className="relative grid grid-cols-5">
        {STEPS.map((step, index) => {
          const done = index < current;
          const active = index === current;
          const date = reachedAt.get(step);
          return (
            <li
              key={step}
              aria-current={active ? "step" : undefined}
              className="flex flex-col items-center gap-1.5 text-center"
            >
              {done ? (
                <span className="flex size-7 items-center justify-center rounded-full bg-brand text-white">
                  <IconCheck />
                </span>
              ) : (
                <span
                  className={`size-7 rounded-full bg-white ${
                    active ? "va-pulse border-4 border-brand" : "border-2 border-[#c9d1df]"
                  }`}
                />
              )}
              <span
                className={`text-[13px] ${
                  active ? "font-extrabold text-brand" : done ? "font-bold" : "font-semibold text-muted"
                }`}
              >
                {t(`applications.step.${step}`)}
              </span>
              <span className="font-mono text-[11px] text-muted">
                {active ? t("detail.current") : date ? formatShortDate(date, i18n.language) : "–"}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
