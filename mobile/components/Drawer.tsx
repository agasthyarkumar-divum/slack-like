import type { PropsWithChildren } from "react";
import { useEffect, useRef } from "react";
import { Animated, Dimensions, Pressable, StyleSheet } from "react-native";

import { useTheme } from "@/lib/theme/ThemeContext";

const DRAWER_WIDTH = Math.min(320, Dimensions.get("window").width * 0.84);
const ANIM_MS = 220;

type DrawerProps = PropsWithChildren<{
  visible: boolean;
  onClose: () => void;
}>;

// A hand-rolled slide-out drawer (Animated + a backdrop Pressable) rather
// than @react-navigation/drawer — that package needs react-native-gesture-handler
// and react-native-reanimated, native modules this project doesn't already
// depend on. This gets the same "hamburger toggle opens a slide-out sidebar"
// behavior with zero new native dependencies.
export function Drawer({ visible, onClose, children }: DrawerProps) {
  const { colors } = useTheme();
  const translateX = useRef(new Animated.Value(-DRAWER_WIDTH)).current;
  const backdropOpacity = useRef(new Animated.Value(0)).current;
  const mountedRef = useRef(visible);
  if (visible) mountedRef.current = true;

  useEffect(() => {
    Animated.timing(translateX, {
      toValue: visible ? 0 : -DRAWER_WIDTH,
      duration: ANIM_MS,
      useNativeDriver: true,
    }).start(() => {
      if (!visible) mountedRef.current = false;
    });
    Animated.timing(backdropOpacity, {
      toValue: visible ? 1 : 0,
      duration: ANIM_MS,
      useNativeDriver: true,
    }).start();
  }, [visible, translateX, backdropOpacity]);

  if (!visible && !mountedRef.current) return null;

  return (
    <>
      <Animated.View
        style={[styles.backdrop, { opacity: backdropOpacity }]}
        pointerEvents={visible ? "auto" : "none"}
      >
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} accessibilityLabel="Close channel list" />
      </Animated.View>
      <Animated.View
        style={[
          styles.drawer,
          { width: DRAWER_WIDTH, backgroundColor: colors.bgSurface, transform: [{ translateX }] },
        ]}
      >
        {children}
      </Animated.View>
    </>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0,0,0,0.32)",
    zIndex: 20,
  },
  drawer: {
    position: "absolute",
    top: 0,
    left: 0,
    bottom: 0,
    zIndex: 21,
  },
});
