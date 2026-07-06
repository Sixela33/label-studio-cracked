import { useCallback, useEffect, useState } from "react";
import { Circle, Group, Image, Rect } from "react-konva";
import Konva from "konva";
import chroma from "chroma-js";
import { observer } from "mobx-react";
import { isDefined } from "../../utils/utilities";
import ReactDOMServer from "react-dom/server";
import React from "react";
import { IconCheck, IconCross } from "@humansignal/icons";

const getItemPosition = (item) => {
  const { shapeRef: shape, bboxCoordsCanvas: bbox } = item;
  let width;
  let height;
  let x;
  let y;

  if (isDefined(bbox)) {
    [width, height, x, y] = [bbox.right - bbox.left, bbox.bottom - bbox.top, bbox.left, bbox.top];
  } else if (isDefined(shape)) {
    [width, height] = [shape?.width() ?? 0, shape?.height() ?? 0];
    [x, y] = [item.x + width / 2 - 32, item.x + width / 2 - 32];
  } else {
    return null;
  }

  return {
    x: x + width / 2 - 32,
    y: y + height + 10,
  };
};

export const SuggestionControls = observer(({ item, useLayer }) => {
  const position = getItemPosition(item);
  const [hovered, setHovered] = useState(false);
  const scale = 1 / item.parent.zoomScale;

  if (position) {
    const size = {
      width: 64,
      height: 32,
    };

    const groupPosition = useLayer
      ? {
          x: 0,
          y: 0,
          scaleX: 1,
          scaleY: 1,
        }
      : {
          x: position.x,
          y: position.y,
          scaleX: scale,
          scaleY: scale,
        };

    // When useLayer is set (brush regions), the controls used to render into their own <Layer>.
    // But this component is already mounted inside a Layer (RegionsLayer), and Konva forbids a
    // Layer nested in a Layer ("You may only add groups and shapes to a layer"). A Group carries
    // the same x/y/scale transform and is legal inside a Layer.
    const wrapperPosition = useLayer
      ? {
          x: position.x,
          y: position.y,
          scaleX: scale,
          scaleY: scale,
        }
      : {};

    const content = (
      <Group
        {...size}
        {...groupPosition}
        opacity={item.highlighted || hovered ? 1 : 0.5}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        <Rect x={0} y={0} width={64} height={32} fill="#000" cornerRadius={16} />
        <ControlButton
          onClick={() => item.annotation.rejectSuggestion(item.id)}
          fill="#CC5E46"
          iconColor="#FFFFFF"
          icon={IconCross}
        />
        <ControlButton
          x={32}
          onClick={() => item.annotation.acceptSuggestion(item.id)}
          fill="#287A72"
          iconColor="#FFFFFF"
          icon={IconCheck}
        />
      </Group>
    );

    return useLayer ? <Group {...wrapperPosition}>{content}</Group> : content;
  }
  return null;
});

const ControlButton = ({ x = 0, fill, iconColor, onClick, icon }) => {
  const [img, setImg] = useState(new window.Image());
  const imageSize = 20;
  const imageOffset = 32 / 2 - imageSize / 2;
  const color = chroma(iconColor ?? "#FFFFFF");
  const [hovered, setHovered] = useState(false);
  const [animatedOpacity, setAnimatedOpacity] = useState(0.2);
  const [animatedFill, setAnimatedFill] = useState("#fff");
  const animationRef = React.useRef();

  useEffect(() => {
    const iconImage = new window.Image();

    iconImage.onload = () => {
      setImg(iconImage);
    };
    iconImage.width = 20;
    iconImage.height = 20;

    const iconElement = React.createElement(icon, { color: iconColor, width: 20, height: 20 });
    const svgString = ReactDOMServer.renderToStaticMarkup(iconElement);
    const base64 = btoa(decodeURIComponent(encodeURIComponent(svgString)));
    iconImage.src = `data:image/svg+xml;base64,${base64}`;
  }, [icon, iconColor]);

  useEffect(() => {
    let start;
    const duration = 150; // ms
    const easeOut = (t) => 1 - (1 - t) ** 2;
    const fromOpacity = animatedOpacity;
    const toOpacity = hovered ? 1 : 0.2;
    const fromFill = chroma(animatedFill);
    const toFill = chroma(hovered ? fill : "#fff");

    function animate(now) {
      if (!start) start = now;
      const elapsed = now - start;
      const t = Math.min(1, elapsed / duration);
      const eased = easeOut(t);
      setAnimatedOpacity(fromOpacity + (toOpacity - fromOpacity) * eased);
      setAnimatedFill(chroma.mix(fromFill, toFill, eased, "rgb").hex());
      if (t < 1) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        setAnimatedOpacity(toOpacity);
        setAnimatedFill(toFill.hex());
      }
    }
    cancelAnimationFrame(animationRef.current);
    animationRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hovered, fill]);

  const applyFilter = useCallback(
    /**
     * @param {import("konva/types/shapes/Image").Image} imgInstance Instance of a Konva Image object
     */
    (imgInstance) => {
      if (imgInstance) {
        const [red, green, blue, alpha] = color.rgba();

        imgInstance.cache();
        imgInstance.setAttrs({
          red,
          green,
          blue,
          alpha,
        });
      }
    },
    [],
  );

  return (
    <Group
      x={x}
      width={32}
      height={32}
      onClick={onClick}
      onMouseEnter={(e) => {
        setHovered(true);
        // Set cursor to pointer
        const stage = e.target.getStage();
        if (stage && stage.container()) {
          stage.container().style.cursor = "pointer";
        }
      }}
      onMouseLeave={(e) => {
        setHovered(false);
        // Reset cursor
        const stage = e.target.getStage();
        if (stage && stage.container()) {
          stage.container().style.cursor = "";
        }
      }}
    >
      <Circle x={16} y={16} radius={14} opacity={animatedOpacity} fill={animatedFill} />
      <Image
        ref={(node) => applyFilter(node)}
        x={imageOffset}
        y={imageOffset}
        width={imageSize}
        height={imageSize}
        image={img}
        filters={[Konva.Filters.RGB]}
      />
    </Group>
  );
};
