import React from 'react';
import { ActivityIndicator, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text } from 'react-native';

import { useStore } from '../state/store';
import { colors } from '../theme/theme';

import DisclaimerScreen from '../screens/DisclaimerScreen';
import AgeGateScreen from '../screens/AgeGateScreen';
import OnboardingScreen from '../screens/OnboardingScreen';
import HomeScreen from '../screens/HomeScreen';
import ToolkitScreen from '../screens/ToolkitScreen';
import ThoughtRecordScreen from '../screens/ThoughtRecordScreen';
import DistortionsScreen from '../screens/DistortionsScreen';
import ValuesScreen from '../screens/ValuesScreen';
import JournalScreen from '../screens/JournalScreen';
import PatternsScreen from '../screens/PatternsScreen';
import QuestsScreen from '../screens/QuestsScreen';
import CrisisScreen from '../screens/CrisisScreen';
import SettingsScreen from '../screens/SettingsScreen';
import FlowRunnerScreen from '../screens/FlowRunnerScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function tabIcon(label: string) {
  return ({ focused }: { focused: boolean }) => (
    <Text style={{ fontSize: 11, color: focused ? colors.primary : colors.textMuted }}>{label}</Text>
  );
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.bg },
        headerShadowVisible: false,
        headerTitleStyle: { color: colors.text },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
      }}
    >
      <Tab.Screen name="Home" component={HomeScreen} options={{ tabBarIcon: tabIcon('Home') }} />
      <Tab.Screen name="Toolkit" component={ToolkitScreen} options={{ tabBarIcon: tabIcon('Tools') }} />
      <Tab.Screen name="Patterns" component={PatternsScreen} options={{ tabBarIcon: tabIcon('Patterns') }} />
      <Tab.Screen name="Quests" component={QuestsScreen} options={{ tabBarIcon: tabIcon('Quests') }} />
      <Tab.Screen name="Settings" component={SettingsScreen} options={{ tabBarIcon: tabIcon('Settings') }} />
    </Tab.Navigator>
  );
}

function Loading() {
  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.bg }}>
      <ActivityIndicator color={colors.primary} />
    </View>
  );
}

export default function RootNavigator() {
  const { ready, disclaimerAck, ageVerified, onboarded } = useStore();

  if (!ready) return <Loading />;

  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{
          headerStyle: { backgroundColor: colors.bg },
          headerShadowVisible: false,
          headerTintColor: colors.primary,
          headerTitleStyle: { color: colors.text },
          contentStyle: { backgroundColor: colors.bg },
        }}
      >
        {!disclaimerAck ? (
          <Stack.Screen name="Disclaimer" component={DisclaimerScreen} options={{ headerShown: false }} />
        ) : !ageVerified ? (
          <Stack.Screen name="AgeGate" component={AgeGateScreen} options={{ headerShown: false }} />
        ) : !onboarded ? (
          <Stack.Screen name="Onboarding" component={OnboardingScreen} options={{ headerShown: false }} />
        ) : (
          <>
            <Stack.Screen name="Main" component={MainTabs} options={{ headerShown: false }} />
            <Stack.Screen name="Flow" component={FlowRunnerScreen} options={{ title: '' }} />
            <Stack.Screen name="Journal" component={JournalScreen} options={{ title: 'Journal' }} />
            <Stack.Screen name="ThoughtRecord" component={ThoughtRecordScreen} options={{ title: 'Thought record' }} />
            <Stack.Screen name="Distortions" component={DistortionsScreen} options={{ title: 'Thinking traps' }} />
            <Stack.Screen name="Values" component={ValuesScreen} options={{ title: 'Your values' }} />
            <Stack.Screen name="Crisis" component={CrisisScreen} options={{ title: 'Support', presentation: 'modal' }} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
