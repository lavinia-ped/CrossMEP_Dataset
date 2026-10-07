import org.apache.poi.openxml4j.opc.*;
import org.apache.xmlbeans.*;
import java.util.*;
import java.lang.reflect.*;
public class Validate {
  static Map<String,String> CLS = new HashMap<>();
  static {
    CLS.put("sld", "org.openxmlformats.schemas.presentationml.x2006.main.SldDocument");
    CLS.put("sldLayout", "org.openxmlformats.schemas.presentationml.x2006.main.SldLayoutDocument");
    CLS.put("sldMaster", "org.openxmlformats.schemas.presentationml.x2006.main.SldMasterDocument");
    CLS.put("notes", "org.openxmlformats.schemas.presentationml.x2006.main.NotesDocument");
    CLS.put("notesMaster", "org.openxmlformats.schemas.presentationml.x2006.main.NotesMasterDocument");
    CLS.put("presentation", "org.openxmlformats.schemas.presentationml.x2006.main.PresentationDocument");
    CLS.put("presentationPr", "org.openxmlformats.schemas.presentationml.x2006.main.PresentationPrDocument");
    CLS.put("viewPr", "org.openxmlformats.schemas.presentationml.x2006.main.ViewPrDocument");
    CLS.put("tblStyleLst", "org.openxmlformats.schemas.drawingml.x2006.main.TblStyleLstDocument");
    CLS.put("theme", "org.openxmlformats.schemas.drawingml.x2006.main.ThemeDocument");
    CLS.put("chartSpace", "org.openxmlformats.schemas.drawingml.x2006.chart.ChartSpaceDocument");
  }
  public static void main(String[] a) throws Exception {
    OPCPackage pkg = OPCPackage.open(a[0], PackageAccess.READ);
    int total = 0;
    for (PackagePart p : pkg.getParts()) {
      String ct = p.getContentType();
      if (!ct.contains("xml") || ct.contains("relationships") || p.getPartName().getName().startsWith("/docProps")) continue;
      String xml = new String(p.getInputStream().readAllBytes(), "UTF-8");
      java.util.regex.Matcher m = java.util.regex.Pattern.compile("<(?:\\w+:)?(\\w+)[\\s>]").matcher(xml.replaceFirst("<\\?xml[^>]*\\?>", ""));
      String root = m.find() ? m.group(1) : "?";
      String cls = CLS.get(root);
      if (cls == null) { System.out.println("SKIP " + p.getPartName() + " root=" + root); continue; }
      Class<?> doc = Class.forName(cls);
      Object factory = doc.getField("Factory").get(null);
      Method parse = factory.getClass().getMethod("parse", String.class, XmlOptions.class);
      XmlObject x;
      try { x = (XmlObject) parse.invoke(factory, xml, new XmlOptions().setLoadLineNumbers()); }
      catch (InvocationTargetException e) { System.out.println("PARSE FAIL " + p.getPartName() + ": " + e.getCause().getMessage()); continue; }
      List<XmlError> errs = new ArrayList<>();
      if (!x.validate(new XmlOptions().setErrorListener(errs))) {
        System.out.println("INVALID " + p.getPartName() + " (" + errs.size() + ")");
        int n = 0;
        for (XmlError e : errs) { if (n++ < 10) System.out.println("   line " + e.getLine() + ": " + e.getMessage()); }
        total += errs.size();
      }
    }
    System.out.println("TOTAL ERRORS " + total);
    pkg.close();
  }
}
