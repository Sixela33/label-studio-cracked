import { Button, Typography } from "@humansignal/ui";
import { Space } from "@humansignal/ui/lib/space/space";
import { cn } from "apps/labelstudio/src/utils/bem";
import { Modal } from "apps/labelstudio/src/components/Modal/ModalPopup";
import { useCallback, useEffect, useRef, useState } from "react";
import { Input } from "../../../components/Form";
import { useAPI } from "../../../providers/ApiProvider";
import { useCopyText } from "../../../hooks/useCopyText";

export function PasswordResetLink({
  pk,
  userPk,
  opened,
  onOpened,
  onClosed,
}: {
  pk?: number | string;
  userPk?: number | string;
  opened: boolean;
  onOpened?: () => void;
  onClosed?: () => void;
}) {
  const api = useAPI();
  const modalRef = useRef<Modal>();
  const [resetUrl, setResetUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, copyText] = useCopyText({ defaultText: resetUrl ?? "" }) as [boolean, (text?: string) => void];

  const fetchResetLink = useCallback(async () => {
    if (!pk || !userPk) return;

    setError(null);
    setResetUrl(null);

    const response = await api.callApi("resetMemberPassword", {
      params: { pk, userPk },
      errorFilter: () => true,
    });

    if (response?.$meta?.ok === false) {
      setError("Could not generate a password reset link.");
      return;
    }

    setResetUrl(location.origin + response.reset_url);
  }, [api, pk, userPk]);

  useEffect(() => {
    if (modalRef.current && opened) {
      modalRef.current?.show?.();
    } else if (modalRef.current && modalRef.current.visible) {
      modalRef.current?.hide?.();
    }
  }, [opened]);

  return (
    <Modal
      ref={modalRef}
      title="Reset member password"
      opened={opened}
      bareFooter={true}
      body={
        <div className={cn("reset-password-link").toClassName()}>
          <Input value={resetUrl ?? ""} style={{ width: "100%" }} readOnly />
          <Typography size="small" className="text-neutral-content-subtler mt-base mb-wider">
            {error ??
              "Copy this one-time link and send it to the member. The link expires once it's used or after 3 days."}
          </Typography>
        </div>
      }
      footer={
        <Space spread>
          <Space />
          <Space>
            <Button
              variant={copied ? "positive" : "primary"}
              className="w-[170px]"
              disabled={!resetUrl}
              onClick={() => copyText()}
              aria-label="Copy password reset link"
            >
              {copied ? "Copied!" : "Copy link"}
            </Button>
          </Space>
        </Space>
      }
      style={{ width: 640, height: 472 }}
      onHide={onClosed}
      onShow={() => {
        fetchResetLink();
        onOpened?.();
      }}
    />
  );
}
