/*
 * XMLParser.java - part of the GATOR project
 *
 * Copyright (c) 2018 The Ohio State University
 *
 * This file is distributed under the terms described in LICENSE in the
 * root directory.
 */
package presto.android.xml;

import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Sets;
import presto.android.Configs;
import presto.android.Logger;
import soot.Scene;
import soot.SootClass;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;

public interface XMLParser {
  abstract class AbstractXMLParser implements XMLParser {
    Map<String, ActivityLaunchMode> activityAndLaunchModes = Maps.newHashMap();

    @Override
    public ActivityLaunchMode getLaunchMode(String activityClassName) {
      return activityAndLaunchModes.get(activityClassName);
    }

    protected String appPkg;

    protected final ArrayList<String> activities = Lists.newArrayList();
    protected final ArrayList<String> services = Lists.newArrayList();
    protected final ArrayList<String> receivers = Lists.newArrayList();
    protected final ArrayList<String> providers = Lists.newArrayList();

    protected final Map<String, Boolean> componentExported = Maps.newHashMap();
    protected final Map<String, String> providerAuthorities = Maps.newHashMap();

    protected SootClass mainActivity;

    @Override
    public SootClass getMainActivity() {
      return mainActivity;
    }

    @Override
    public Iterator<String> getActivities() {
      return activities.iterator();
    }

    @Override
    public Iterator<String> getReceivers() {
      return receivers.iterator();
    }

    @Override
    public Iterator<String> getServices() {
      return services.iterator();
    }

    @Override
    public Iterator<String> getProviders() {
      return providers.iterator();
    }

    @Override
    public boolean isComponentExported(String className) {
      return componentExported.getOrDefault(className, false);
    }

    @Override
    public String getProviderAuthorities(String className) {
      return providerAuthorities.get(className);
    }

    @Override
    public int getNumberOfActivities() {
      return activities.size();
    }

    @Override
    public String getAppPackageName() {
      return appPkg;
    }
  }

  class Helper {
    // These are declared in the manifest, but no corresponding .java/.class
    // files are available. Most likely, code was deleted while manifest has
    // not been updated.
    static Set<String> astridMissingActivities = Sets.newHashSet(
            "com.todoroo.astrid.tags.reusable.FeaturedListActivity",
            "com.todoroo.astrid.actfm.TagViewWrapperActivity",
            "com.todoroo.astrid.actfm.TagCreateActivity",
            "com.todoroo.astrid.gtasks.auth.GtasksAuthTokenProvider",
            "com.todoroo.astrid.reminders.NotificationWrapperActivity");
    static Set<String> nprMissingActivities = Sets.newHashSet(
            "com.crittercism.NotificationActivity");

    public static String getClassName(String classNameFromXml, String appPkg) {
      if ('.' == classNameFromXml.charAt(0)) {
        classNameFromXml = appPkg + classNameFromXml;
      }
      if (!classNameFromXml.contains(".")) {
        classNameFromXml = appPkg + "." + classNameFromXml;
      }
      if (Configs.benchmarkName.equals("Astrid")
              && astridMissingActivities.contains(classNameFromXml)) {
        return null;
      }
      if (Configs.benchmarkName.equals("NPR")
              && nprMissingActivities.contains(classNameFromXml)) {
        return null;
      }
      if (Scene.v().getSootClass(classNameFromXml).isPhantom()) {
        Logger.verb("XMLParser", "[WARNNING] : " + classNameFromXml +
                " is declared in AndroidManifest.xml, but phantom.");
        return null;
        // throw new RuntimeException(
        //     classNameFromXml + " is declared in AndroidManifest.xml, but phantom.");
      }
      return classNameFromXml;
    }
  }

  // A hacky factory method. It's good enough since the number of possible
  // XMLParser implementations is very limited. We may even end up with only
  // one and push the diff logic into the existing parser.
  class Factory {
    public static XMLParser getXMLParser() {
      return DefaultXMLParser.v();
    }
  }
  // === layout, id, string, menu xml files

  // R.layout.*
  Set<Integer> getApplicationLayoutIdValues();

  Set<Integer> getSystemLayoutIdValues();

  Integer getSystemRLayoutValue(String layoutName);

  String getApplicationRLayoutName(Integer value);

  String getSystemRLayoutName(Integer value);

  // R.menu.*
  Set<Integer> getApplicationMenuIdValues();

  Set<Integer> getSystemMenuIdValues();

  String getApplicationRMenuName(Integer value);

  String getSystemRMenuName(Integer value);

  // R.id.*
  Set<Integer> getApplicationRIdValues();

  Set<Integer> getSystemRIdValues();

  Integer getSystemRIdValue(String idName);

  String getApplicationRIdName(Integer value);

  String getSystemRIdName(Integer value);

  // R.string.*
  Set<Integer> getStringIdValues();

  String getRStringName(Integer value);

  String getStringValue(Integer idValue);

  // === AndroidManifest.xml
  SootClass getMainActivity();

  Iterator<String> getActivities();

  Iterator<String> getServices();

  Iterator<String> getReceivers();

  Iterator<String> getProviders();

  boolean isComponentExported(String className);

  String getProviderAuthorities(String className);

  Integer getApplicationIdValue(String type, String name);

  Integer getSystemIdValue(String type, String name);

  int getNumberOfActivities();

  String getAppPackageName();

  enum ActivityLaunchMode {
    standard,
    singleTop,
    singleTask,
    singleInstance
  }

  ActivityLaunchMode getLaunchMode(String activityClassName);

  // === APIs for layout xml files

  // Given a view id, find static abstraction of the matched view.
  AndroidView findViewById(Integer id);

}
